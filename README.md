# Parsefy Python SDK

Official Python SDK for [Parsefy](https://parsefy.io) - Financial Document Infrastructure for Developers.

Parsefy turns financial PDFs (invoices, receipts, bills) into structured JSON with validation and confidence scores. We return **validated output or fail loudly** - no silent errors.

## Installation

```bash
pip install parsefy
```

## Quick Start

```python
from parsefy import Parsefy
from pydantic import BaseModel, Field

# Initialize client (reads PARSEFY_API_KEY from environment)
client = Parsefy()

# Define your extraction schema
class Invoice(BaseModel):
    invoice_number: str = Field(description="The invoice number")
    date: str = Field(description="Invoice date in YYYY-MM-DD format")
    total: float = Field(description="Total amount")
    vendor: str = Field(description="Vendor company name")

# Extract data from a document
result = client.extract(file="invoice.pdf", schema=Invoice)

if result.error is None:
    print(f"Invoice #{result.data.invoice_number}")
    print(f"Total: ${result.data.total}")
    print(f"Confidence: {result.meta.confidence_score}")
else:
    print(f"Error: {result.error.message}")
```

## Features

- **Validated extraction** - Get structured data or clear error messages, never silent failures
- **Confidence scores** - Per-field confidence with source evidence
- **Type-safe** - Full type inference with Pydantic models
- **Sync & async** - Both `extract()` and `extract_async()` methods
- **Configurable threshold** - Balance speed vs accuracy with `confidence_threshold`

## Understanding Required vs Optional Fields

> **This is critical for controlling costs.**

By default, **ALL fields are required**. If a required field cannot be extracted with sufficient confidence, the fallback model is triggered, which costs more credits.

### Required Fields (Default)

```python
class Invoice(BaseModel):
    # These are REQUIRED - will trigger fallback if not found confidently
    invoice_number: str = Field(description="The invoice number")
    total: float = Field(description="Total amount")
```

### Optional Fields

To mark a field as optional, you **must** provide a default value of `None`:

```python
class Invoice(BaseModel):
    # Required
    invoice_number: str = Field(description="The invoice number")
    total: float = Field(description="Total amount")

    # Optional - won't trigger fallback if missing
    po_number: str | None = Field(default=None, description="PO number if present")
    notes: str | None = Field(default=None, description="Additional notes")
```

### Common Mistake

```python
# WRONG - This is still required (just nullable)
po_number: str | None  # Missing default value!

# CORRECT - This is truly optional
po_number: str | None = None
```

### Best Practice

Only mark fields as required if they **must** be present in all documents. Making rarely-present fields required will trigger expensive fallback models frequently.

## Confidence Threshold

Control the trade-off between speed and accuracy:

```python
# Lower threshold = faster (accepts Tier 1 more often)
result = client.extract(
    file="invoice.pdf",
    schema=Invoice,
    confidence_threshold=0.75
)

# Higher threshold = more accurate (triggers Tier 2 fallback more often)
result = client.extract(
    file="invoice.pdf",
    schema=Invoice,
    confidence_threshold=0.95
)
```

Default: `0.85`

## Working with Confidence Scores

Every extraction includes detailed confidence information:

```python
result = client.extract(file="invoice.pdf", schema=Invoice)

if result.error is None:
    # Overall confidence
    print(f"Overall confidence: {result.meta.confidence_score}")

    # Per-field confidence with evidence
    for field in result.meta.field_confidence:
        print(f"{field.field}: {field.score}")
        print(f"  Reason: {field.reason}")
        print(f"  Source: '{field.text}' (page {field.page})")

    # Any issues detected
    if result.meta.issues:
        print("Issues:", result.meta.issues)
```

Example output:

```
Overall confidence: 0.94
$.invoice_number: 0.98
  Reason: Exact match
  Source: 'Invoice # INV-2024-0042' (page 1)
$.total: 0.92
  Reason: Formatting ambiguous
  Source: 'Total: $1,250.00' (page 1)
```

## Authentication

Set your API key via environment variable:

```bash
export PARSEFY_API_KEY=pk_your_api_key
```

Or pass it directly:

```python
client = Parsefy(api_key="pk_your_api_key")
```

## Usage Examples

### Complex Invoice Schema

```python
from parsefy import Parsefy
from pydantic import BaseModel, Field

client = Parsefy()

class LineItem(BaseModel):
    description: str = Field(description="Item description")
    quantity: int = Field(description="Quantity ordered")
    unit_price: float = Field(description="Price per unit")
    total: float = Field(description="Line total")

class Invoice(BaseModel):
    # Required fields
    invoice_number: str = Field(description="Invoice number")
    vendor: str = Field(description="Vendor company name")
    date: str = Field(description="Invoice date (YYYY-MM-DD)")
    total: float = Field(description="Total amount due")

    # Optional fields - won't trigger fallback if missing
    line_items: list[LineItem] | None = Field(
        default=None,
        description="List of items on the invoice"
    )
    tax: float | None = Field(default=None, description="Tax amount")
    po_number: str | None = Field(default=None, description="Purchase order number")

result = client.extract(file="invoice.pdf", schema=Invoice)

if result.error is None:
    print(f"Invoice #{result.data.invoice_number}")
    print(f"From: {result.data.vendor}")
    print(f"Total: ${result.data.total}")

    if result.data.line_items:
        for item in result.data.line_items:
            print(f"  - {item.description}: {item.quantity} x ${item.unit_price}")
```

### Async Processing

```python
import asyncio
from parsefy import Parsefy
from pydantic import BaseModel, Field

class Receipt(BaseModel):
    store_name: str = Field(description="Name of the store")
    total: float = Field(description="Total amount paid")
    date: str | None = Field(default=None, description="Purchase date")

async def process_receipts():
    async with Parsefy() as client:
        tasks = [
            client.extract_async(file=f"receipt_{i}.pdf", schema=Receipt)
            for i in range(1, 4)
        ]
        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results, 1):
            if result.error is None:
                print(f"Receipt {i}: {result.data.store_name} - ${result.data.total}")
                print(f"  Confidence: {result.meta.confidence_score}")

asyncio.run(process_receipts())
```

### Error Handling

```python
from parsefy import Parsefy, APIError, ValidationError
from pydantic import BaseModel

client = Parsefy()

class Invoice(BaseModel):
    number: str
    total: float

try:
    result = client.extract(file="invoice.pdf", schema=Invoice)

    if result.error is None:
        print(result.data)
        print(f"Confidence: {result.meta.confidence_score}")
    else:
        # Extraction-level error (API returned 200 but extraction failed)
        print(f"Extraction failed: {result.error.code}")
        print(f"Message: {result.error.message}")

except ValidationError as e:
    # Client-side validation error (file not found, wrong type, etc.)
    print(f"Validation error: {e.message}")

except APIError as e:
    # HTTP error from API (401, 429, 500, etc.)
    print(f"API error {e.status_code}: {e.message}")
```

## API Reference

### `Parsefy` Client

```python
client = Parsefy(
    api_key: str | None = None,      # API key (or set PARSEFY_API_KEY env var)
    timeout: float = 60.0,           # Request timeout in seconds
)
```

### `extract()` / `extract_async()`

```python
result = client.extract(
    file: str | Path | bytes | BinaryIO,  # Document to extract from
    schema: type[T],                       # Pydantic model class
    confidence_threshold: float = 0.85,   # Min confidence (0-1)
) -> ExtractResult[T]
```

### `ExtractResult[T]`

| Field | Type | Description |
|-------|------|-------------|
| `data` | `T \| None` | Extracted data (or None on error) |
| `meta` | `ExtractionMeta \| None` | Confidence scores and evidence |
| `metadata` | `ExtractionMetadata` | Processing metadata |
| `error` | `APIErrorDetail \| None` | Error details (or None on success) |

### `ExtractionMeta`

| Field | Type | Description |
|-------|------|-------------|
| `confidence_score` | `float` | Overall confidence (0-1) |
| `field_confidence` | `list[FieldConfidence]` | Per-field confidence |
| `issues` | `list[str]` | Detected issues/warnings |

### `FieldConfidence`

| Field | Type | Description |
|-------|------|-------------|
| `field` | `str` | JSON path (e.g., `$.invoice_number`) |
| `score` | `float` | Confidence score (0-1) |
| `reason` | `str` | Explanation for the score |
| `page` | `int` | Page number |
| `text` | `str` | Source text extracted |

### `ExtractionMetadata`

| Field | Type | Description |
|-------|------|-------------|
| `processing_time_ms` | `int` | Processing time in milliseconds |
| `input_tokens` | `int` | Input tokens used |
| `output_tokens` | `int` | Output tokens generated |
| `credits` | `int` | Credits consumed (1 credit = 1 page) |
| `fallback_triggered` | `bool` | Whether fallback model was used |

## Supported File Types

- PDF (`.pdf`)
- Microsoft Word (`.docx`)

Maximum file size: 10MB

## Requirements

- Python 3.10+
- Pydantic 2.0+
- httpx 0.25+

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [Documentation](https://docs.parsefy.io)
- [Parsefy Website](https://parsefy.io)
