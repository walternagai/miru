"""File content extraction module."""

import sys
from pathlib import Path


class UnsupportedFileTypeError(Exception):
    """Raised when file type is not supported."""

    SUPPORTED_EXTENSIONS = [
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".sh",
        ".yaml",
        ".yml",
        ".json",
        ".csv",
        ".xml",
        ".html",
        ".pdf",
        ".docx",
    ]

    def __init__(self, path: str, extension: str) -> None:
        self.path = path
        self.extension = extension
        msg = f"Tipo de arquivo não suportado: {extension}. "
        msg += f"Suportados: {', '.join(self.SUPPORTED_EXTENSIONS)}"
        super().__init__(msg)


class FileExtractionError(Exception):
    """Raised when file extraction fails."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{reason}")


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".csv",
    ".xml",
    ".html",
}


def extract_text(path: str | Path) -> tuple[str, str]:
    """
    Extract text from file and return (filename, extracted_text).

    Args:
        path: Path to file

    Returns:
        Tuple of (filename, extracted_text)

    Raises:
        FileNotFoundError: File does not exist
        UnsupportedFileTypeError: Extension not supported
        FileExtractionError: Extraction failed (corrupt PDF, etc.)
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    if not path_obj.is_file():
        raise FileNotFoundError(f"Não é um arquivo: {path}")

    filename = path_obj.name
    suffix = path_obj.suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        text = _extract_text_file(path_obj)
        return filename, text

    if suffix == ".pdf":
        text = _extract_pdf(path_obj, filename)
        return filename, text

    if suffix == ".docx":
        text = _extract_docx(path_obj, filename)
        return filename, text

    raise UnsupportedFileTypeError(str(path), suffix)


def _extract_text_file(path: Path) -> str:
    """Extract text from plain text file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_pdf(path: Path, filename: str) -> str:
    """Extract text from PDF file using pdfplumber."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise FileExtractionError(
            str(path),
            "pdfplumber não instalado. Instale com: pip install pdfplumber",
        )

    try:
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)

            if not pages:
                raise FileExtractionError(
                    str(path),
                    f"PDF escaneado ou sem texto extraível em {filename}.\n"
                    "Pré-processe com OCR antes de usar --file.\n"
                    "Alternativa: use uma ferramenta como 'ocrmypdf' para adicionar camada de texto.",
                )

            return "\n\n".join(pages)
    except FileExtractionError:
        raise
    except Exception as e:
        raise FileExtractionError(str(path), f"Falha ao extrair PDF: {e}") from e


def _extract_docx(path: Path, filename: str) -> str:
    """Extract text from DOCX file using python-docx."""
    try:
        from docx import Document  # type: ignore
    except ImportError:
        raise FileExtractionError(
            str(path),
            "python-docx não instalado. Instale com: pip install python-docx",
        )

    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n\n".join(paragraphs)
    except Exception as e:
        raise FileExtractionError(str(path), f"Falha ao extrair DOCX: {e}") from e


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.

    Simple estimation: len(text) // 4

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def check_context_limit(
    text: str,
    max_ctx: int,
    filename: str,
    threshold: float = 0.9,
) -> bool:
    """
    Check if text is within context limit.

    Args:
        text: Text to check
        max_ctx: Maximum context tokens
        filename: File name for warning message
        threshold: Threshold percentage (default 0.9 = 90%)

    Returns:
        True if text is within limit or user confirms, False otherwise
    """
    estimated = estimate_tokens(text)
    threshold_tokens = int(threshold * max_ctx)

    if estimated <= threshold_tokens:
        return True

    print(
        f"⚠ {filename} → ~{estimated} tokens estimados",
        file=sys.stderr,
    )
    print(
        f"  Contexto disponível: {max_ctx} tokens ({int(threshold * 100)}% = {threshold_tokens})",
        file=sys.stderr,
    )
    print("  Isso pode truncar a resposta. Continuar? [s/N]", file=sys.stderr)

    try:
        response = input().strip().lower()
        return response in ("s", "sim", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def format_for_prompt(filename: str, text: str) -> str:
    """
    Format file content for injection into prompt.

    Args:
        filename: File name
        text: Extracted text

    Returns:
        Formatted text with delimiters
    """
    return f"[Conteúdo de {filename}]\n{text}\n[Fim de {filename}]"