"""Tests for miru/commands/compare.py CLI — argument validation and error paths."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestCompareCliValidation:
    def test_requires_two_models(self) -> None:
        result = runner.invoke(app, ["compare", "gemma3", "--prompt", "x"])
        assert result.exit_code == 1

    def test_requires_prompt(self) -> None:
        result = runner.invoke(app, ["compare", "a", "b"])
        assert result.exit_code == 1

    def test_prompt_and_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("prompt", encoding="utf-8")
        result = runner.invoke(
            app, ["compare", "a", "b", "--prompt", "x", "--prompt-file", str(f)]
        )
        assert result.exit_code == 1

    def test_invalid_format(self) -> None:
        result = runner.invoke(app, ["compare", "a", "b", "--prompt", "x", "--format", "xml"])
        assert result.exit_code == 1

    def test_system_and_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("sys", encoding="utf-8")
        result = runner.invoke(
            app, ["compare", "a", "b", "--prompt", "x", "--system", "s", "--system-file", str(f)]
        )
        assert result.exit_code == 1

    def test_missing_system_file(self) -> None:
        result = runner.invoke(
            app, ["compare", "a", "b", "--prompt", "x", "--system-file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_file_audio_rejected(self, tmp_path) -> None:
        f = tmp_path / "f.txt"
        f.write_text("data", encoding="utf-8")
        result = runner.invoke(
            app, ["compare", "a", "b", "--prompt", "x", "--file", str(f)]
        )
        assert result.exit_code == 1

    def test_prompt_file_read(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("prompt do arquivo", encoding="utf-8")
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt-file", str(f), "--quiet"]
            )
            assert result.exit_code == 0
            # async runs inside asyncio.run; mock called with final prompt
            assert mock_cmp.called

    def test_json_format_success(self) -> None:
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            mock_cmp.return_value = []
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt", "x", "--format", "json"]
            )
            assert result.exit_code == 0


class TestCompareCliMore:
    def test_system_from_file(self, tmp_path) -> None:
        f = tmp_path / "sys.txt"
        f.write_text("seja conciso", encoding="utf-8")
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt", "x", "--system-file", str(f), "--quiet"]
            )
            assert result.exit_code == 0
            assert mock_cmp.called

    def test_prompt_file_read(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("prompt do arquivo", encoding="utf-8")
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt-file", str(f), "--quiet"]
            )
            assert result.exit_code == 0
            assert mock_cmp.called

    def test_prompt_file_missing_exits(self) -> None:
        result = runner.invoke(app, ["compare", "a", "b", "--prompt-file", "nope.txt"])
        assert result.exit_code == 1

    def test_json_output_format(self, tmp_path) -> None:
        f = tmp_path / "sys.txt"
        f.write_text("s", encoding="utf-8")
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            mock_cmp.return_value = []
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt-file", str(f), "--format", "json", "--quiet"]
            )
            assert result.exit_code == 0


class TestCompareVisionErrors:
    def test_vision_connection_error(self) -> None:
        """Imagem + OllamaConnectionError → exit 1."""
        from miru.ollama.client import OllamaConnectionError

        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_cmp:
            mock_cmp.side_effect = OllamaConnectionError("down")
            result = runner.invoke(
                app, ["compare", "a", "b", "--prompt", "x", "--image", "foto.png", "--quiet"]
            )
            assert result.exit_code == 1
