"""Utility functions for the Parsefy SDK."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def is_supported_file(path: str | Path) -> bool:
    """Check if a file path has a supported extension."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get the lowercase file extension from a filename."""
    return Path(filename).suffix.lower()

