"""Tests for miru/commands/run.py CLI — validation and error paths."""

from unittest.mock import AsyncMock, patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestRunCli:
    def test_invalid_format(self) -> None:
        result = runner.invoke(app, ["run", "gemma3", "prompt", "--format", "xml"])
        assert result.exit_code == 1

    def test_system_and_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("sys", encoding="utf-8")
        result = runner.invoke(
            app, ["run", "gemma3", "prompt", "--system", "x", "--system-file", str(f)]
        )
        assert result.exit_code == 1

    def test_missing_system_file(self) -> None:
        result = runner.invoke(
            app, ["run", "gemma3", "prompt", "--system-file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_missing_input_file(self) -> None:
        result = runner.invoke(
            app, ["run", "gemma3", "prompt", "--file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_success_text(self) -> None:
        with patch("miru.commands.run._run_async", new_callable=AsyncMock) as mock_run:
            result = runner.invoke(app, ["run", "gemma3", "olá"])
            assert result.exit_code == 0
            assert mock_run.called

    def test_connection_error(self) -> None:
        from miru.ollama.client import OllamaConnectionError

        with patch("miru.commands.run._run_async", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = OllamaConnectionError("Cannot connect")
            result = runner.invoke(app, ["run", "gemma3", "olá"])
            assert result.exit_code == 1

    def test_model_not_found(self) -> None:
        from miru.ollama.client import OllamaModelNotFound

        with patch("miru.commands.run._run_async", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = OllamaModelNotFound("not found")
            result = runner.invoke(app, ["run", "gemma3", "olá"])
            assert result.exit_code == 1
