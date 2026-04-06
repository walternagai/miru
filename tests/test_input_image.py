"""Tests for miru/input/image.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from miru.input.image import (
    ImageFormatError,
    ImageNotFoundError,
    encode_image,
    encode_images,
)


class TestEncodeImage:
    """Tests for encode_image function."""

    def test_encode_valid_jpeg(self, tmp_path: Path) -> None:
        """Should encode valid JPEG file to base64."""
        img_path = tmp_path / "test.jpg"
        with open(img_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")

        b64 = encode_image(img_path)
        
        assert isinstance(b64, str)
        assert len(b64) > 0
        assert not b64.startswith("data:")

    def test_encode_returns_pure_base64(self, tmp_path: Path) -> None:
        """Should return base64 string without data URI prefix."""
        img_path = tmp_path / "test.png"
        with open(img_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        b64 = encode_image(img_path)
        
        assert not b64.startswith("data:image")
        assert not b64.startswith("data:")

    def test_encode_nonexistent_file(self) -> None:
        """Should raise ImageNotFoundError for missing file."""
        with pytest.raises(ImageNotFoundError) as exc_info:
            encode_image("nonexistent.jpg")
        
        assert "nonexistent.jpg" in str(exc_info.value)

    def test_encode_unsupported_format(self, tmp_path: Path) -> None:
        """Should raise ImageFormatError for unsupported format."""
        img_path = tmp_path / "test.bmp"
        
        with open(img_path, "wb") as f:
            f.write(b"BM" + b"\x00" * 100)
        
        with pytest.raises(ImageFormatError) as exc_info:
            encode_image(img_path)
        
        assert "não suportado" in str(exc_info.value)

    def test_large_image_warning(self, tmp_path: Path, capsys) -> None:
        """Should display warning for images > 10MB."""
        img_path = tmp_path / "large.jpg"
        large_data = b"0" * (11 * 1024 * 1024)
        with open(img_path, "wb") as f:
            f.write(large_data)

        encode_image(img_path)
        
        captured = capsys.readouterr()
        assert "11.0MB" in captured.err
        assert "imagens grandes podem impactar performance" in captured.err

    def test_encode_multiple_images(self, tmp_path: Path) -> None:
        """Should encode list of images."""
        img1 = tmp_path / "img1.jpg"
        img2 = tmp_path / "img2.png"
        
        with open(img1, "wb") as f:
            f.write(b"test1")
        with open(img2, "wb") as f:
            f.write(b"test2")

        results = encode_images([img1, img2])
        
        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)


class TestImageExceptions:
    """Tests for custom exceptions."""

    def test_image_not_found_error(self) -> None:
        """Should create ImageNotFoundError with correct message."""
        error = ImageNotFoundError("test.jpg")
        assert "test.jpg" in str(error)
        assert error.path == "test.jpg"

    def test_image_format_error_with_format(self) -> None:
        """Should create ImageFormatError with format info."""
        error = ImageFormatError("test.bmp", "BMP")
        assert error.detected_format == "BMP"
        assert "BMP" in str(error)
        assert "JPEG" in str(error)

    def test_image_format_error_without_format(self) -> None:
        """Should create ImageFormatError without format info."""
        error = ImageFormatError("test.xyz", None)
        assert error.detected_format is None
        assert "não suportado" in str(error)

    def test_image_format_error_message(self, tmp_path: Path) -> None:
        """Should include supported formats in error message."""
        img_path = tmp_path / "test.tiff"
        
        with open(img_path, "wb") as f:
            f.write(b"fake image content")
        
        with pytest.raises(ImageFormatError) as exc_info:
            encode_image(img_path)
        
        assert "não suportado" in str(exc_info.value)