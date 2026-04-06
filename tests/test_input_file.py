"""Tests for miru/input/file.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from miru.input.file import (
    FileExtractionError,
    UnsupportedFileTypeError,
    estimate_tokens,
    extract_text,
    format_for_prompt,
)


class TestExtractText:
    """Tests for extract_text function."""

    def test_extract_text_file(self, tmp_path: Path) -> None:
        """Should extract text from plain text file."""
        text_file = tmp_path / "main.py"
        text_file.write_text("import asyncio\nprint('hello')")

        filename, content = extract_text(text_file)

        assert filename == "main.py"
        assert "import asyncio" in content
        assert "print('hello')" in content

    def test_extract_markdown_file(self, tmp_path: Path) -> None:
        """Should extract text from markdown file."""
        md_file = tmp_path / "README.md"
        md_file.write_text("# Title\n\nContent")

        filename, content = extract_text(md_file)

        assert filename == "README.md"
        assert "# Title" in content

    def test_extract_nonexistent_file(self) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            extract_text("nonexistent.txt")

    def test_extract_unsupported_format(self, tmp_path: Path) -> None:
        """Should raise UnsupportedFileTypeError for unsupported format."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("content")

        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            extract_text(unsupported_file)

        assert ".xyz" in str(exc_info.value)
        assert ".txt" in str(exc_info.value)

    def test_extract_pdf_file(self, tmp_path: Path) -> None:
        """Should extract text from PDF file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%fake pdf content")

        mock_pdfplumber = MagicMock()
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content here"
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
            from miru.input.file import extract_text
            
            filename, content = extract_text(pdf_file)

            assert filename == "test.pdf"
            assert "PDF content here" in content

    def test_extract_scanned_pdf(self, tmp_path: Path) -> None:
        """Should raise FileExtractionError for scanned PDF."""
        pdf_file = tmp_path / "scanned.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%fake pdf content")

        mock_pdfplumber = MagicMock()
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        with patch.dict("sys.modules", {"pdfplumber": mock_pdfplumber}):
            from miru.input.file import extract_text
            
            with pytest.raises(FileExtractionError) as exc_info:
                extract_text(pdf_file)

            assert "PDF escaneado" in str(exc_info.value)
            assert "OCR" in str(exc_info.value)

    def test_extract_docx_file(self, tmp_path: Path) -> None:
        """Should extract text from DOCX file."""
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"fake docx content")

        mock_document_class = MagicMock()
        mock_doc = MagicMock()
        mock_doc.paragraphs = [MagicMock(text="Paragraph 1"), MagicMock(text="Paragraph 2")]
        mock_document_class.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": MagicMock(Document=mock_document_class)}):
            from miru.input.file import extract_text
            
            filename, content = extract_text(docx_file)

            assert filename == "test.docx"
            assert "Paragraph 1" in content
            assert "Paragraph 2" in content

    def test_extract_pdf_without_pdfplumber(self, tmp_path: Path) -> None:
        """Should raise FileExtractionError if pdfplumber not installed."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%fake pdf content")

        with patch.dict("sys.modules", {"pdfplumber": None}):
            with pytest.raises(FileExtractionError) as exc_info:
                from miru.input.file import extract_text
                extract_text(pdf_file)

            assert "pdfplumber" in str(exc_info.value).lower()


class TestEstimateTokens:
    """Tests for estimate_tokens function."""

    def test_estimate_tokens_basic(self) -> None:
        """Should estimate tokens as len(text) // 4."""
        text = "This is a test string"
        tokens = estimate_tokens(text)

        assert tokens == len(text) // 4
        assert tokens == 5

    def test_estimate_tokens_empty(self) -> None:
        """Should return 0 for empty text."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_unicode(self) -> None:
        """Should handle unicode characters."""
        text = "Olá mundo! 你好世界"
        tokens = estimate_tokens(text)

        assert tokens == len(text) // 4


class TestFormatForPrompt:
    """Tests for format_for_prompt function."""

    def test_format_basic(self) -> None:
        """Should format content with delimiters."""
        result = format_for_prompt("test.txt", "Hello world")

        assert "[Conteúdo de test.txt]" in result
        assert "Hello world" in result
        assert "[Fim de test.txt]" in result

    def test_format_multiline(self) -> None:
        """Should handle multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        result = format_for_prompt("file.py", content)

        assert "[Conteúdo de file.py]" in result
        assert "Line 1" in result
        assert "Line 3" in result


class TestFileExceptions:
    """Tests for custom exceptions."""

    def test_unsupported_file_type_error(self) -> None:
        """Should create UnsupportedFileTypeError with correct message."""
        error = UnsupportedFileTypeError("test.xyz", ".xyz")

        assert error.path == "test.xyz"
        assert error.extension == ".xyz"
        assert ".xyz" in str(error)
        assert ".txt" in str(error)

    def test_file_extraction_error(self) -> None:
        """Should create FileExtractionError with reason."""
        error = FileExtractionError("test.pdf", "PDF is corrupt")

        assert error.path == "test.pdf"
        assert error.reason == "PDF is corrupt"
        assert "PDF is corrupt" in str(error)


class TestTextExtensions:
    """Tests for various text file extensions."""

    @pytest.mark.parametrize("ext", [".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".xml", ".html"])
    def test_text_extensions(self, tmp_path: Path, ext: str) -> None:
        """Should extract content from all text file extensions."""
        text_file = tmp_path / f"test{ext}"
        text_file.write_text("sample content")

        filename, content = extract_text(text_file)

        assert filename == f"test{ext}"
        assert content == "sample content"