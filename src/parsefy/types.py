"""Type definitions for the Parsefy SDK."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


class FieldConfidence(BaseModel):
    """Confidence information for a single extracted field."""

    field: str = Field(description="JSON path to the field (e.g., '$.invoice_number')")
    score: float = Field(description="Confidence score between 0 and 1")
    reason: str = Field(description="Explanation for the confidence score")
    page: int | None = Field(description="Page number where the field was found (1-based), or None if not found on a specific page")
    text: str | None = Field(description="Source text that was extracted, or None if inferred")


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
    credits: int
    fallback_triggered: bool


class APIErrorDetail(BaseModel):
    """Error information when extraction fails."""

    code: str
    message: str


class VerificationCheck(BaseModel):
    """Individual math verification check result."""

    type: str = Field(description="Type of verification check (e.g., 'HORIZONTAL_SUM', 'VERTICAL_SUM')")
    status: str = Field(description="Status of the check: 'PASSED', 'FAILED', or 'CANNOT_VERIFY'")
    fields: list[str] = Field(description="Fields involved in this verification check")
    passed: bool = Field(description="Whether the check passed")
    delta: float = Field(description="Difference between expected and actual values")
    expected: float = Field(description="Expected value from the verification rule")
    actual: float = Field(description="Actual value extracted from the document")


class Verification(BaseModel):
    """
    Math verification results for extracted numeric data.
    
    This provides deterministic verification of mathematical consistency
    (e.g., totals, subtotals, taxes, line item sums).
    """

    status: str = Field(
        description="Overall verification status: 'PASSED', 'FAILED', 'PARTIAL', 'CANNOT_VERIFY', or 'NO_RULES'"
    )
    checks_passed: int = Field(description="Number of verification checks that passed")
    checks_failed: int = Field(description="Number of verification checks that failed")
    cannot_verify_count: int = Field(description="Number of checks that could not be verified")
    checks_run: list[VerificationCheck] = Field(
        default_factory=list,
        description="Detailed results for each verification check performed"
    )


class ExtractResult(BaseModel, Generic[T]):
    """
    Result of an extraction operation.

    On success: `data` contains the extracted object, `error` is None.
    On failure: `data` is None, `error` contains error details.
    
    The `meta` field provides detailed confidence scores and evidence for
    each extracted field, enabling you to make informed decisions about
    whether to trust the extraction or require manual review.
    
    The `verification` field contains math verification results when
    `enable_verification=True` is used in the extraction request.
    """

    data: T | None = None
    meta: ExtractionMeta | None = Field(
        default=None,
        description="Field-level confidence scores and extraction evidence"
    )
    metadata: ExtractionMetadata
    verification: Verification | None = Field(
        default=None,
        description="Math verification results (only present when enable_verification=True)"
    )
    error: APIErrorDetail | None = None
