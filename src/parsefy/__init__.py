"""
Parsefy - Official Python SDK for AI-powered document data extraction.

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
    ```
"""

from parsefy.client import Parsefy
from parsefy.errors import APIError, ExtractionError, ParsefyError, ValidationError
from parsefy.types import APIErrorDetail, ExtractResult, ExtractionMetadata

__version__ = "1.0.0"

__all__ = [
    "Parsefy",
    "ParsefyError",
    "APIError",
    "ExtractionError",
    "ValidationError",
    "ExtractResult",
    "ExtractionMetadata",
    "APIErrorDetail",
]


