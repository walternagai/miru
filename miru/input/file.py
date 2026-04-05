"""File content extraction module."""

import mimetypes
from pathlib import Path


def extract_file_content(file_path: str) -> str:
    """
    Extract text content from file.

    Supports:
        - Plain text files (.txt, .md, .csv, .json, .xml, .yaml, .yml)
        - PDF files (.pdf) - requires PyPDF2 or pdfplumber
        - Code files (.py, .js, .java, .cpp, .c, .h, etc.)

    Args:
        file_path: Path to file

    Returns:
        Extracted text content

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is not supported or extraction fails
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    suffix = path.suffix.lower()

    text_extensions = {
        ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml",
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
        ".sh", ".bash", ".zsh", ".fish",
        ".html", ".htm", ".css", ".scss", ".sass", ".less",
        ".sql", ".db", ".sqlite",
        ".r", ".rmd", ".jl",
        ".toml", ".ini", ".cfg", ".conf",
    }

    if suffix in text_extensions:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    if suffix == ".pdf":
        return _extract_pdf(path)

    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type and mime_type.startswith("text/"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(1000)
            if content.isprintable() or "\n" in content:
                with open(path, "r", encoding="utf-8", errors="replace") as f_full:
                    return f_full.read()
    except Exception:
        pass

    raise ValueError(
        f"Unsupported file format: {suffix}. "
        f"Supported formats: text files, PDF, and code files."
    )


def _extract_pdf(path: Path) -> str:
    """
    Extract text from PDF file.

    Args:
        path: Path to PDF file

    Returns:
        Extracted text

    Raises:
        ValueError: If PDF extraction fails or library not installed
    """
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            raise ValueError(
                "PDF extraction requires PyPDF2 or pdfplumber. "
                "Install with: pip install PyPDF2 or pip install pdfplumber"
            )
    except Exception as e:
        raise ValueError(f"Failed to extract PDF content: {e}") from e