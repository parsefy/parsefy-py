"""Type definitions for the Parsefy SDK."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


class FieldConfidence(BaseModel):
    """Confidence information for a single extracted field."""

    field: str = Field(description="JSON path to the field (e.g., '$.invoice_number')")
    score: float = Field(description="Confidence score between 0 and 1")
    reason: str = Field(description="Explanation for the confidence score")
    page: int = Field(description="Page number where the field was found")
    text: str = Field(description="Source text that was extracted")


class ExtractionMeta(BaseModel):
    """
    Detailed extraction metadata with confidence scores and field-level evidence.
    
    This provides transparency into how confident the model is about each
    extracted field, along with the source text used for extraction.
    """

    confidence_score: float = Field(
        description="Overall confidence score for the extraction (0-1)"
    )
    field_confidence: list[FieldConfidence] = Field(
        default_factory=list,
        description="Per-field confidence scores with evidence"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Any issues or warnings detected during extraction"
    )


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""

    model_config = ConfigDict(populate_by_name=True)

    processing_time_ms: int = Field(alias="processing_time_ms")
    input_tokens: int
    output_tokens: int
    credits: int
    fallback_triggered: bool


class APIErrorDetail(BaseModel):
    """Error information when extraction fails."""

    code: str
    message: str


class ExtractResult(BaseModel, Generic[T]):
    """
    Result of an extraction operation.

    On success: `data` contains the extracted object, `error` is None.
    On failure: `data` is None, `error` contains error details.
    
    The `meta` field provides detailed confidence scores and evidence for
    each extracted field, enabling you to make informed decisions about
    whether to trust the extraction or require manual review.
    """

    data: T | None = None
    meta: ExtractionMeta | None = Field(
        default=None,
        description="Field-level confidence scores and extraction evidence"
    )
    metadata: ExtractionMetadata
    error: APIErrorDetail | None = None
