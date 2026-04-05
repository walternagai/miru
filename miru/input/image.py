"""Image encoding module for vision models."""

import base64
from pathlib import Path


def encode_image(image_path: str) -> str:
    """
    Encode image file to base64 string.

    Args:
        image_path: Path to image file

    Returns:
        Base64-encoded string

    Raises:
        FileNotFoundError: If image file does not exist
        ValueError: If file is not a valid image
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {image_path}")

    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Not a valid image format: {path.suffix}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_images(image_paths: list[str]) -> list[str]:
    """
    Encode multiple image files to base64 strings.

    Args:
        image_paths: List of image file paths

    Returns:
        List of base64-encoded strings

    Raises:
        FileNotFoundError: If any image file does not exist
        ValueError: If any file is not valid
    """
    return [encode_image(path) for path in image_paths]