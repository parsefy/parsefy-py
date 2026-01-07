"""Custom exception classes for the Parsefy SDK."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from parsefy.types import ExtractionMetadata


class ParsefyError(Exception):
    """Base exception for all Parsefy errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code


class APIError(ParsefyError):
    """Raised when the API returns an HTTP error (4xx/5xx)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ExtractionError(ParsefyError):
    """Raised when extraction fails (returned in response.error)."""

    def __init__(
        self,
        message: str,
        code: str,
        metadata: "ExtractionMetadata",
    ):
        super().__init__(message, code)
        self.metadata = metadata


class ValidationError(ParsefyError):
    """Raised for client-side validation errors."""

    pass


