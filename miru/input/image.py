"""Image encoding module for vision models."""

import base64
import sys
from pathlib import Path


class ImageNotFoundError(Exception):
    """Raised when image file is not found."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Image not found: {path}")


class ImageFormatError(Exception):
    """Raised when image format is not supported."""

    SUPPORTED = ["JPEG", "PNG", "GIF", "WEBP"]

    def __init__(self, path: str, detected_format: str | None) -> None:
        self.path = path
        self.detected_format = detected_format
        if detected_format:
            msg = f"Formato {detected_format} não suportado. Suportados: {', '.join(self.SUPPORTED)}"
        else:
            msg = f"Formato não suportado. Suportados: {', '.join(self.SUPPORTED)}"
        super().__init__(msg)


def encode_image(path: str | Path) -> str:
    """
    Validate, optionally resize, and return image as base64 string.

    Args:
        path: Path to image file

    Returns:
        Base64-encoded string (pure, no data URI prefix)

    Raises:
        ImageNotFoundError: File does not exist
        ImageFormatError: Format is not supported
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise ImageNotFoundError(str(path))

    if not path_obj.is_file():
        raise ImageNotFoundError(str(path))

    size_bytes = path_obj.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > 10:
        print(
            f"⚠ {path_obj.name} tem {size_mb:.1f}MB — imagens grandes podem impactar performance.",
            file=sys.stderr,
        )

    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    suffix = path_obj.suffix.lower()

    try:
        from PIL import Image  # type: ignore

        with Image.open(path_obj) as img:
            img_format = img.format
            if img_format not in ImageFormatError.SUPPORTED:
                raise ImageFormatError(str(path), img_format)
    except ImportError:
        if suffix not in valid_extensions:
            raise ImageFormatError(str(path), None)
    except ImageFormatError:
        raise
    except Exception as e:
        raise ImageFormatError(str(path), None) from e

    with open(path_obj, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_images(paths: list[str | Path]) -> list[str]:
    """
    Process a list of images and return list of base64 strings.

    Args:
        paths: List of image file paths

    Returns:
        List of base64-encoded strings

    Raises:
        ImageNotFoundError: If any image file does not exist
        ImageFormatError: If any file is not valid
    """
    return [encode_image(path) for path in paths]
