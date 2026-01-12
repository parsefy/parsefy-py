"""Tests for the Parsefy client."""

import os
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from parsefy import Parsefy, APIError, ValidationError, ExtractResult


class SampleSchema(BaseModel):
    """Sample schema for testing."""

    name: str = Field(description="A name field")
    value: int = Field(description="A numeric value")


class SampleSchemaWithOptional(BaseModel):
    """Sample schema with optional field for testing."""

    name: str = Field(description="A name field")
    value: int = Field(description="A numeric value")
    notes: str | None = Field(default=None, description="Optional notes")


class TestParsefyInit:
    """Tests for Parsefy client initialization."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with direct API key."""
        client = Parsefy(api_key="test_key")
        assert client.api_key == "test_key"
        client.close()

    def test_init_with_env_var(self) -> None:
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"PARSEFY_API_KEY": "env_key"}):
            client = Parsefy()
            assert client.api_key == "env_key"
            client.close()

    def test_init_without_api_key_raises(self) -> None:
        """Test that initialization without API key raises ValidationError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop("PARSEFY_API_KEY", None)
            with pytest.raises(ValidationError) as exc_info:
                Parsefy()
            assert "API key is required" in str(exc_info.value)

    def test_init_with_custom_timeout(self) -> None:
        """Test initialization with custom timeout."""
        client = Parsefy(api_key="test_key", timeout=120.0)
        assert client.timeout == 120.0
        client.close()


class TestStripTitles:
    """Tests for title stripping optimization."""

    @pytest.fixture
    def client(self) -> Parsefy:
        """Create a test client."""
        client = Parsefy(api_key="test_key")
        yield client
        client.close()

    def test_strip_titles_removes_titles(self, client: Parsefy) -> None:
        """Test that _strip_titles removes title fields."""
        schema = {
            "title": "MyModel",
            "type": "object",
            "properties": {
                "name": {"title": "Name", "type": "string"},
                "value": {"title": "Value", "type": "integer"},
            },
        }

        client._strip_titles(schema)

        assert "title" not in schema
        assert "title" not in schema["properties"]["name"]
        assert "title" not in schema["properties"]["value"]

    def test_strip_titles_handles_nested_objects(self, client: Parsefy) -> None:
        """Test that _strip_titles handles nested structures."""
        schema = {
            "title": "Parent",
            "type": "object",
            "properties": {
                "child": {
                    "title": "Child",
                    "type": "object",
                    "properties": {
                        "name": {"title": "Name", "type": "string"}
                    }
                }
            }
        }

        client._strip_titles(schema)

        assert "title" not in schema
        assert "title" not in schema["properties"]["child"]
        assert "title" not in schema["properties"]["child"]["properties"]["name"]

    def test_strip_titles_handles_arrays(self, client: Parsefy) -> None:
        """Test that _strip_titles handles arrays."""
        schema = {
            "title": "Model",
            "type": "object",
            "properties": {
                "items": {
                    "title": "Items",
                    "type": "array",
                    "items": {"title": "Item", "type": "string"}
                }
            }
        }

        client._strip_titles(schema)

        assert "title" not in schema
        assert "title" not in schema["properties"]["items"]
        assert "title" not in schema["properties"]["items"]["items"]


class TestPrepareFile:
    """Tests for file preparation logic."""

    @pytest.fixture
    def client(self) -> Parsefy:
        """Create a test client."""
        client = Parsefy(api_key="test_key")
        yield client
        client.close()

    def test_prepare_file_from_path_string(self, client: Parsefy, tmp_path: Path) -> None:
        """Test preparing file from path string."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        filename, content, mime_type = client._prepare_file(str(pdf_file))

        assert filename == "test.pdf"
        assert content == b"%PDF-1.4 test content"
        assert mime_type == "application/pdf"

    def test_prepare_file_from_path_object(self, client: Parsefy, tmp_path: Path) -> None:
        """Test preparing file from Path object."""
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"docx content")

        filename, content, mime_type = client._prepare_file(docx_file)

        assert filename == "test.docx"
        assert content == b"docx content"
        assert (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_prepare_file_from_bytes(self, client: Parsefy) -> None:
        """Test preparing file from bytes."""
        filename, content, mime_type = client._prepare_file(b"raw bytes content")

        assert filename == "document.pdf"
        assert content == b"raw bytes content"
        assert mime_type == "application/pdf"

    def test_prepare_file_from_file_object(self, client: Parsefy) -> None:
        """Test preparing file from file-like object."""
        file_obj = BytesIO(b"file object content")
        file_obj.name = "uploaded.pdf"

        filename, content, mime_type = client._prepare_file(file_obj)

        assert filename == "uploaded.pdf"
        assert content == b"file object content"
        assert mime_type == "application/pdf"

    def test_prepare_file_not_found(self, client: Parsefy) -> None:
        """Test that non-existent file raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            client._prepare_file("/nonexistent/path/file.pdf")
        assert "File not found" in str(exc_info.value)

    def test_prepare_file_unsupported_type(self, client: Parsefy, tmp_path: Path) -> None:
        """Test that unsupported file type raises ValidationError."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_bytes(b"text content")

        with pytest.raises(ValidationError) as exc_info:
            client._prepare_file(txt_file)
        assert "Unsupported file type" in str(exc_info.value)

    def test_prepare_file_empty(self, client: Parsefy, tmp_path: Path) -> None:
        """Test that empty file raises ValidationError."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        with pytest.raises(ValidationError) as exc_info:
            client._prepare_file(empty_file)
        assert "File is empty" in str(exc_info.value)

    def test_prepare_file_too_large(self, client: Parsefy, tmp_path: Path) -> None:
        """Test that file exceeding size limit raises ValidationError."""
        large_file = tmp_path / "large.pdf"
        # Write 11MB of data
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))

        with pytest.raises(ValidationError) as exc_info:
            client._prepare_file(large_file)
        assert "exceeds maximum allowed size" in str(exc_info.value)


class TestParseResponse:
    """Tests for response parsing logic."""

    @pytest.fixture
    def client(self) -> Parsefy:
        """Create a test client."""
        client = Parsefy(api_key="test_key")
        yield client
        client.close()

    def test_parse_successful_response(self, client: Parsefy) -> None:
        """Test parsing a successful API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": {"name": "Test", "value": 42},
            "_meta": {
                "confidence_score": 0.95,
                "field_confidence": [
                    {
                        "field": "$.name",
                        "score": 0.98,
                        "reason": "Exact match",
                        "page": 1,
                        "text": "Test"
                    },
                    {
                        "field": "$.value",
                        "score": 0.92,
                        "reason": "Numeric extraction",
                        "page": 1,
                        "text": "42"
                    },
                ],
                "issues": [],
            },
            "metadata": {
                "processing_time_ms": 1500,
                "credits": 1,
                "fallback_triggered": False,
            },
            "error": None,
        }

        result = client._parse_response(mock_response, SampleSchema)

        assert isinstance(result, ExtractResult)
        assert result.data is not None
        assert result.data.name == "Test"
        assert result.data.value == 42
        assert result.meta is not None
        assert result.meta.confidence_score == 0.95
        assert len(result.meta.field_confidence) == 2
        assert result.meta.field_confidence[0].field == "$.name"
        assert result.meta.field_confidence[0].score == 0.98
        assert result.metadata.processing_time_ms == 1500
        assert result.metadata.credits == 1
        assert result.error is None

    def test_parse_response_without_meta(self, client: Parsefy) -> None:
        """Test parsing a response without _meta field (backward compatibility)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": {"name": "Test", "value": 42},
            "metadata": {
                "processing_time_ms": 1500,
                "credits": 1,
                "fallback_triggered": False,
            },
            "error": None,
        }

        result = client._parse_response(mock_response, SampleSchema)

        assert result.data is not None
        assert result.meta is None  # No _meta in response
        assert result.error is None

    def test_parse_extraction_error_response(self, client: Parsefy) -> None:
        """Test parsing a response with extraction error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": None,
            "_meta": {
                "confidence_score": 0.3,
                "field_confidence": [],
                "issues": ["Could not identify invoice number"],
            },
            "metadata": {
                "processing_time_ms": 500,
                "credits": 1,
                "fallback_triggered": True,
            },
            "error": {
                "code": "EXTRACTION_FAILED",
                "message": "Could not extract data from document",
            },
        }

        result = client._parse_response(mock_response, SampleSchema)

        assert result.data is None
        assert result.error is not None
        assert result.error.code == "EXTRACTION_FAILED"
        assert "Could not extract" in result.error.message
        assert result.metadata.fallback_triggered is True
        assert result.meta is not None
        assert len(result.meta.issues) == 1

    def test_parse_http_error_response(self, client: Parsefy) -> None:
        """Test that HTTP errors raise APIError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        with pytest.raises(APIError) as exc_info:
            client._parse_response(mock_response, SampleSchema)

        assert exc_info.value.status_code == 401
        assert "401" in exc_info.value.message


class TestSchemaGeneration:
    """Tests for schema generation and required fields."""

    def test_required_fields_in_schema(self) -> None:
        """Test that all non-optional fields are marked as required."""
        schema = SampleSchema.model_json_schema()

        assert "required" in schema
        assert "name" in schema["required"]
        assert "value" in schema["required"]

    def test_optional_fields_not_required(self) -> None:
        """Test that optional fields are not in required array."""
        schema = SampleSchemaWithOptional.model_json_schema()

        assert "required" in schema
        assert "name" in schema["required"]
        assert "value" in schema["required"]
        assert "notes" not in schema["required"]


class TestContextManager:
    """Tests for context manager functionality."""

    def test_sync_context_manager(self) -> None:
        """Test synchronous context manager."""
        with Parsefy(api_key="test_key") as client:
            assert client.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test asynchronous context manager."""
        async with Parsefy(api_key="test_key") as client:
            assert client.api_key == "test_key"


class TestVerification:
    """Tests for math verification functionality."""

    @pytest.fixture
    def client(self) -> Parsefy:
        """Create a test client."""
        client = Parsefy(api_key="test_key")
        yield client
        client.close()

    def test_parse_response_with_verification(self, client: Parsefy) -> None:
        """Test parsing a response with verification results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": {"name": "Test", "value": 42},
            "_meta": {
                "confidence_score": 0.95,
                "field_confidence": [],
                "issues": [],
            },
            "metadata": {
                "processing_time_ms": 1500,
                "credits": 1,
                "fallback_triggered": False,
            },
            "verification": {
                "status": "PASSED",
                "checks_passed": 1,
                "checks_failed": 0,
                "cannot_verify_count": 0,
                "checks_run": [
                    {
                        "type": "HORIZONTAL_SUM",
                        "status": "PASSED",
                        "fields": ["total", "subtotal", "tax"],
                        "passed": True,
                        "delta": 0.0,
                        "expected": 1250.00,
                        "actual": 1250.00,
                    }
                ],
            },
            "error": None,
        }

        result = client._parse_response(mock_response, SampleSchema)

        assert result.verification is not None
        assert result.verification.status == "PASSED"
        assert result.verification.checks_passed == 1
        assert result.verification.checks_failed == 0
        assert len(result.verification.checks_run) == 1
        assert result.verification.checks_run[0].type == "HORIZONTAL_SUM"
        assert result.verification.checks_run[0].passed is True
        assert result.verification.checks_run[0].delta == 0.0

    def test_parse_response_without_verification(self, client: Parsefy) -> None:
        """Test parsing a response without verification (default behavior)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": {"name": "Test", "value": 42},
            "_meta": {
                "confidence_score": 0.95,
                "field_confidence": [],
                "issues": [],
            },
            "metadata": {
                "processing_time_ms": 1500,
                "credits": 1,
                "fallback_triggered": False,
            },
            "error": None,
        }

        result = client._parse_response(mock_response, SampleSchema)

        assert result.verification is None
