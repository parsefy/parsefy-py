"""Tests for utility functions."""

from pathlib import Path

from parsefy.utils import get_file_extension, is_supported_file


class TestIsSupportedFile:
    """Tests for is_supported_file function."""

    def test_pdf_supported(self) -> None:
        """Test that PDF files are supported."""
        assert is_supported_file("document.pdf") is True
        assert is_supported_file("DOCUMENT.PDF") is True
        assert is_supported_file(Path("document.pdf")) is True

    def test_docx_supported(self) -> None:
        """Test that DOCX files are supported."""
        assert is_supported_file("document.docx") is True
        assert is_supported_file("DOCUMENT.DOCX") is True
        assert is_supported_file(Path("document.docx")) is True

    def test_unsupported_files(self) -> None:
        """Test that other file types are not supported."""
        assert is_supported_file("document.txt") is False
        assert is_supported_file("document.doc") is False
        assert is_supported_file("document.xlsx") is False
        assert is_supported_file("image.png") is False


class TestGetFileExtension:
    """Tests for get_file_extension function."""

    def test_lowercase_extension(self) -> None:
        """Test extracting lowercase extension."""
        assert get_file_extension("document.pdf") == ".pdf"
        assert get_file_extension("document.docx") == ".docx"

    def test_uppercase_extension(self) -> None:
        """Test that uppercase extensions are lowercased."""
        assert get_file_extension("DOCUMENT.PDF") == ".pdf"
        assert get_file_extension("Document.DOCX") == ".docx"

    def test_path_with_directories(self) -> None:
        """Test extracting extension from full path."""
        assert get_file_extension("/path/to/document.pdf") == ".pdf"
        assert get_file_extension("./relative/path/document.docx") == ".docx"

    def test_no_extension(self) -> None:
        """Test file with no extension."""
        assert get_file_extension("document") == ""

    def test_multiple_dots(self) -> None:
        """Test file with multiple dots."""
        assert get_file_extension("document.backup.pdf") == ".pdf"

