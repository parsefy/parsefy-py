"""
Parsefy - Financial Document Infrastructure for Developers.

Parsefy turns financial PDFs (invoices, receipts, bills) into structured JSON
with validation and confidence scores. We return validated output or fail
loudly - no silent errors.

Example:
    ```python
    from parsefy import Parsefy
    from pydantic import BaseModel, Field

    client = Parsefy()

    class Invoice(BaseModel):
        # Required fields
        invoice_number: str = Field(description="The invoice number")
        total: float = Field(description="Total amount")

        # Optional field (won't trigger fallback if missing)
        po_number: str | None = Field(default=None, description="PO number")

    result = client.extract(file="invoice.pdf", schema=Invoice)

    if result.error is None:
        print(result.data.invoice_number)
        print(f"Confidence: {result.meta.confidence_score}")
    ```

Important:
    All fields are REQUIRED by default. If a required field can't be extracted
    with sufficient confidence, the fallback model is triggered (more expensive).

    Mark fields as optional with: `field_name: str | None = None`
"""

from parsefy.client import Parsefy
from parsefy.errors import APIError, ExtractionError, ParsefyError, ValidationError
from parsefy.types import (
    APIErrorDetail,
    ExtractResult,
    ExtractionMeta,
    ExtractionMetadata,
    FieldConfidence,
)

__version__ = "1.1.0"

__all__ = [
    "Parsefy",
    "ParsefyError",
    "APIError",
    "ExtractionError",
    "ValidationError",
    "ExtractResult",
    "ExtractionMeta",
    "ExtractionMetadata",
    "FieldConfidence",
    "APIErrorDetail",
]
