"""Type definitions for the Parsefy SDK."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound=BaseModel)


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
    """

    data: T | None = None
    metadata: ExtractionMetadata
    error: APIErrorDetail | None = None

