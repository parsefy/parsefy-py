"""Parsefy API client for financial document data extraction."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, BinaryIO, TypeVar

import httpx
from pydantic import BaseModel

from parsefy.errors import APIError, ValidationError
from parsefy.types import (
    APIErrorDetail,
    ExtractResult,
    ExtractionMeta,
    ExtractionMetadata,
    FieldConfidence,
)

T = TypeVar("T", bound=BaseModel)

# Supported file types
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BASE_URL = "https://api.parsefy.io"
DEFAULT_CONFIDENCE_THRESHOLD = 0.85


class Parsefy:
    """
    Parsefy API client for financial document data extraction.

    Parsefy turns financial PDFs (invoices, receipts, bills) into structured
    JSON with validation and confidence scores. We return validated output
    or fail loudly - no silent errors.

    Args:
        api_key: Your Parsefy API key. If not provided, reads from
                 PARSEFY_API_KEY environment variable.
        timeout: Request timeout in seconds (default: 60)

    Important - Required vs Optional Fields:
        By default, ALL fields in your Pydantic model are required. If a required
        field cannot be extracted with sufficient confidence, the fallback model
        is triggered (which costs more credits).

        To mark a field as optional, use: `field_name: str | None = None`

        Example:
            ```python
            class Invoice(BaseModel):
                # REQUIRED - will trigger fallback if not found confidently
                invoice_number: str = Field(description="The invoice number")
                total: float = Field(description="Total amount")

                # OPTIONAL - won't trigger fallback if missing
                po_number: str | None = Field(default=None, description="PO number if present")
                notes: str | None = Field(default=None, description="Additional notes")
            ```

        Tip: Only mark fields as required if they MUST be present. Making rarely-
        present fields required will trigger expensive fallback models frequently.

    Example:
        ```python
        from parsefy import Parsefy
        from pydantic import BaseModel, Field

        client = Parsefy()

        class Invoice(BaseModel):
            invoice_number: str = Field(description="The invoice number")
            total: float = Field(description="Total amount")

        result = client.extract(file="invoice.pdf", schema=Invoice)

        if result.error is None:
            print(result.data.invoice_number)
            print(f"Confidence: {result.meta.confidence_score}")
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.environ.get("PARSEFY_API_KEY")
        if not self.api_key:
            raise ValidationError(
                "API key is required. Pass it directly or set PARSEFY_API_KEY environment variable."
            )

        self.timeout = timeout

        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        self._async_client: httpx.AsyncClient | None = None

    def _get_async_client(self) -> httpx.AsyncClient:
        """Lazily create async client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._async_client

    def _strip_titles(self, schema: Any) -> None:
        """
        Recursively remove 'title' keys from schema to save tokens.

        Pydantic adds a 'title' field to every property by default, which
        wastes tokens and adds noise for the LLM.
        """
        if isinstance(schema, dict):
            if "title" in schema:
                del schema["title"]
            for value in schema.values():
                self._strip_titles(value)
        elif isinstance(schema, list):
            for item in schema:
                self._strip_titles(item)

    def _prepare_file(
        self,
        file: str | Path | bytes | BinaryIO,
    ) -> tuple[str, bytes, str]:
        """
        Prepare file for upload.

        Returns:
            Tuple of (filename, file_bytes, content_type)
        """
        if isinstance(file, (str, Path)):
            path = Path(file)
            if not path.exists():
                raise ValidationError(f"File not found: {path}")

            suffix = path.suffix.lower()
            if suffix not in MIME_TYPES:
                raise ValidationError(
                    f"Unsupported file type: {suffix}. Only PDF and DOCX are supported."
                )

            content_type = MIME_TYPES[suffix]
            file_bytes = path.read_bytes()
            filename = path.name

        elif isinstance(file, bytes):
            # For bytes, we can't determine type - default to PDF
            file_bytes = file
            filename = "document.pdf"
            content_type = "application/pdf"

        else:
            # File-like object
            file_bytes = file.read()
            filename = getattr(file, "name", "document.pdf")
            suffix = Path(filename).suffix.lower()
            content_type = MIME_TYPES.get(suffix, "application/pdf")

        if len(file_bytes) == 0:
            raise ValidationError("File is empty.")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise ValidationError(
                f"File size ({len(file_bytes)} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)."
            )

        return filename, file_bytes, content_type

    def _parse_response(
        self,
        response: httpx.Response,
        schema: type[T],
    ) -> ExtractResult[T]:
        """Parse API response into ExtractResult."""
        if response.status_code != 200:
            try:
                error_detail = response.json()
            except Exception:
                error_detail = response.text

            raise APIError(
                message=f"API request failed with status {response.status_code}",
                status_code=response.status_code,
                response=error_detail,
            )

        data = response.json()

        metadata = ExtractionMetadata(
            processing_time_ms=data["metadata"]["processing_time_ms"],
            input_tokens=data["metadata"]["input_tokens"],
            output_tokens=data["metadata"]["output_tokens"],
            credits=data["metadata"]["credits"],
            fallback_triggered=data["metadata"]["fallback_triggered"],
        )

        # Parse the new _meta structure
        meta = None
        if data.get("_meta"):
            meta_data = data["_meta"]
            field_confidence = [
                FieldConfidence(
                    field=fc["field"],
                    score=fc["score"],
                    reason=fc["reason"],
                    page=fc["page"],
                    text=fc["text"],
                )
                for fc in meta_data.get("field_confidence", [])
            ]
            meta = ExtractionMeta(
                confidence_score=meta_data["confidence_score"],
                field_confidence=field_confidence,
                issues=meta_data.get("issues", []),
            )

        error = None
        if data.get("error"):
            error = APIErrorDetail(
                code=data["error"]["code"],
                message=data["error"]["message"],
            )

        extracted_data = None
        if data.get("object") is not None:
            extracted_data = schema.model_validate(data["object"])

        return ExtractResult[T](
            data=extracted_data,
            meta=meta,
            metadata=metadata,
            error=error,
        )

    def extract(
        self,
        *,
        file: str | Path | bytes | BinaryIO,
        schema: type[T],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> ExtractResult[T]:
        """
        Extract structured data from a financial document (synchronous).

        Args:
            file: Document to extract from. Can be:
                  - str or Path: Path to the file
                  - bytes: Raw file contents
                  - BinaryIO: File-like object
            schema: Pydantic model class defining the extraction schema.
                    Use Field(description="...") to guide the AI.
            confidence_threshold: Minimum confidence score (0-1) for extraction.
                    Default: 0.85. Lower = faster (accepts Tier 1 more often).
                    Higher = more accurate (triggers Tier 2 fallback more often).

        Returns:
            ExtractResult containing:
            - data: Extracted data as the schema type (or None on error)
            - meta: Field-level confidence scores and evidence
            - metadata: Processing metadata (tokens, time, credits)
            - error: Error details if extraction failed (or None on success)

        Raises:
            ValidationError: If file is invalid (not found, wrong type, too large)
            APIError: If the API returns an HTTP error (4xx/5xx)

        Important - Required Fields & Billing:
            ALL fields are required by default. If a required field's confidence
            is below the threshold, the fallback model is triggered (more credits).

            To avoid unexpected costs, mark rarely-present fields as optional:
            `field_name: str | None = None`

        Example:
            ```python
            class Invoice(BaseModel):
                # Required fields - MUST be present
                invoice_number: str = Field(description="Invoice number")
                total: float = Field(description="Total amount")

                # Optional field - won't trigger fallback if missing
                po_number: str | None = Field(default=None, description="PO number")

            result = client.extract(file="invoice.pdf", schema=Invoice)

            if result.error is None:
                print(result.data.invoice_number)
                print(f"Confidence: {result.meta.confidence_score}")

                # Check individual field confidence
                for field in result.meta.field_confidence:
                    print(f"{field.field}: {field.score} - {field.reason}")
            else:
                print(f"Error: {result.error.message}")
            ```
        """
        filename, file_bytes, content_type = self._prepare_file(file)

        # Convert Pydantic model to JSON Schema and optimize for tokens
        json_schema = schema.model_json_schema()
        self._strip_titles(json_schema)

        response = self._client.post(
            f"{BASE_URL}/v1/extract",
            files={"file": (filename, file_bytes, content_type)},
            data={
                "output_schema": json.dumps(json_schema),
                "confidence_threshold": str(confidence_threshold),
            },
        )

        return self._parse_response(response, schema)

    async def extract_async(
        self,
        *,
        file: str | Path | bytes | BinaryIO,
        schema: type[T],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> ExtractResult[T]:
        """
        Extract structured data from a financial document (asynchronous).

        Same as extract() but async. See extract() for full documentation.

        Args:
            file: Document to extract from
            schema: Pydantic model class defining the extraction schema
            confidence_threshold: Minimum confidence score (0-1). Default: 0.85

        Example:
            ```python
            result = await client.extract_async(
                file="invoice.pdf",
                schema=Invoice,
                confidence_threshold=0.9  # Higher accuracy
            )
            ```
        """
        filename, file_bytes, content_type = self._prepare_file(file)

        json_schema = schema.model_json_schema()
        self._strip_titles(json_schema)

        client = self._get_async_client()
        response = await client.post(
            f"{BASE_URL}/v1/extract",
            files={"file": (filename, file_bytes, content_type)},
            data={
                "output_schema": json.dumps(json_schema),
                "confidence_threshold": str(confidence_threshold),
            },
        )

        return self._parse_response(response, schema)

    def close(self) -> None:
        """Close the HTTP client connections."""
        self._client.close()
        if self._async_client:
            # Note: async client should be closed with await
            pass

    async def aclose(self) -> None:
        """Close the HTTP client connections (async)."""
        self._client.close()
        if self._async_client:
            await self._async_client.aclose()

    def __enter__(self) -> "Parsefy":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    async def __aenter__(self) -> "Parsefy":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
