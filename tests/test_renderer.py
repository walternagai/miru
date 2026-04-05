"""Tests for miru/renderer.py."""

import pytest

from miru.renderer import format_date, format_size


class TestFormatSize:
    """Tests for format_size function."""

    def test_format_size_gb(self) -> None:
        """Should format bytes to GB."""
        result = format_size(5_368_709_120)  # 5 GB
        assert "GB" in result
        assert "5.0" in result

    def test_format_size_mb(self) -> None:
        """Should format bytes to MB."""
        result = format_size(524_288_000)  # 500 MB
        assert "MB" in result
        assert "500" in result

    def test_format_size_kb(self) -> None:
        """Should format bytes to KB."""
        result = format_size(51_200)  # 50 KB
        assert "KB" in result
        assert "50" in result

    def test_format_size_bytes(self) -> None:
        """Should format small sizes as bytes."""
        result = format_size(512)
        assert "B" in result
        assert "512" in result

    def test_format_size_zero(self) -> None:
        """Should handle zero size."""
        result = format_size(0)
        assert "0 B" == result


class TestFormatDate:
    """Tests for format_date function."""

    def test_format_date_iso(self) -> None:
        """Should format ISO date."""
        result = format_date("2026-04-01T12:00:00Z")
        assert "2026-04-01" == result

    def test_format_date_date_only(self) -> None:
        """Should handle date-only format."""
        result = format_date("2026-04-01")
        assert "2026-04-01" == result

    def test_format_date_empty(self) -> None:
        """Should handle empty date."""
        result = format_date("")
        assert "-" == result

    def test_format_date_invalid(self) -> None:
        """Should handle invalid date."""
        result = format_date("invalid")
        assert "invalid" == result