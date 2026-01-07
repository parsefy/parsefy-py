# Parsefy Python SDK

Official Python SDK for [Parsefy](https://parsefy.io) - AI-powered document data extraction.

Extract structured data from PDF and DOCX documents using Pydantic models. Simply define your schema and let Parsefy handle the rest.

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
    currency: str = Field(description="3-letter currency code")

# Extract data from a document
result = client.extract(file="invoice.pdf", schema=Invoice)

if result.error is None:
    print(f"Invoice #{result.data.invoice_number}")
    print(f"Total: {result.data.total} {result.data.currency}")
    print(f"Credits used: {result.metadata.credits}")
else:
    print(f"Error: {result.error.message}")
```

## Features

- **Type-safe extraction** - Full type inference with Pydantic models
- **Sync & async support** - Both `extract()` and `extract_async()` methods
- **Multiple input types** - File paths, bytes, or file-like objects
- **Detailed metadata** - Processing time, token usage, and credits consumed
- **Client-side validation** - File type, size, and existence checks before upload

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

### Basic Extraction

```python
from parsefy import Parsefy
from pydantic import BaseModel, Field

client = Parsefy()

class Person(BaseModel):
    name: str = Field(description="Full name of the person")
    email: str = Field(description="Email address")
    phone: str | None = Field(default=None, description="Phone number if present")

result = client.extract(file="contact.pdf", schema=Person)

if result.error is None:
    print(result.data.name)
    print(result.data.email)
```

### Complex Schemas

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
    invoice_number: str = Field(description="Invoice number")
    vendor: str = Field(description="Vendor company name")
    date: str = Field(description="Invoice date (YYYY-MM-DD)")
    line_items: list[LineItem] = Field(description="List of items on the invoice")
    subtotal: float = Field(description="Subtotal before tax")
    tax: float = Field(description="Tax amount")
    total: float = Field(description="Total amount due")

result = client.extract(file="invoice.pdf", schema=Invoice)

if result.error is None:
    for item in result.data.line_items:
        print(f"{item.description}: {item.quantity} x ${item.unit_price}")
```

### Async Usage

```python
import asyncio
from parsefy import Parsefy
from pydantic import BaseModel, Field

class Receipt(BaseModel):
    store_name: str = Field(description="Name of the store")
    total: float = Field(description="Total amount paid")

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

asyncio.run(process_receipts())
```

### Different Input Types

```python
from parsefy import Parsefy
from pydantic import BaseModel
from pathlib import Path

client = Parsefy()

class Document(BaseModel):
    title: str
    content: str

# From file path string
result = client.extract(file="document.pdf", schema=Document)

# From Path object
result = client.extract(file=Path("document.pdf"), schema=Document)

# From bytes
with open("document.pdf", "rb") as f:
    file_bytes = f.read()
result = client.extract(file=file_bytes, schema=Document)

# From file object
with open("document.pdf", "rb") as f:
    result = client.extract(file=f, schema=Document)
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
) -> ExtractResult[T]
```

### `ExtractResult[T]`

| Field | Type | Description |
|-------|------|-------------|
| `data` | `T \| None` | Extracted data (or None on error) |
| `metadata` | `ExtractionMetadata` | Processing metadata |
| `error` | `APIErrorDetail \| None` | Error details (or None on success) |

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
