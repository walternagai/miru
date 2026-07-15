"""Tests for miru/commands/list.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from miru.cli import app

runner = CliRunner()


class TestListCommand:
    """Tests for miru list command."""

    def test_list_models_text_format(self) -> None:
        """Should display models in table format."""
        mock_models = [
            {
                "name": "gemma3:latest",
                "size": 5368709120,
                "modified_at": "2026-04-01T12:00:00Z",
            },
            {
                "name": "llava:latest",
                "size": 4294967296,
                "modified_at": "2026-03-15T10:30:00Z",
            },
        ]

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_models

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "gemma3:latest" in result.output
            assert "5.0 GB" in result.output
            assert "2 modelo(s) disponível(is)" in result.output

    def test_list_models_json_format(self) -> None:
        """Should output valid JSON with --format json."""
        mock_models = [
            {
                "name": "gemma3:latest",
                "size": 5368709120,
                "modified_at": "2026-04-01T12:00:00Z",
            },
        ]

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_models

            result = runner.invoke(app, ["list", "--format", "json"])

            assert result.exit_code == 0
            # Validate JSON output
            output = json.loads(result.output.strip())
            assert len(output) == 1
            assert output[0]["name"] == "gemma3:latest"
            assert "size_human" in output[0]

    def test_list_models_quiet_mode(self) -> None:
        """Should output only model names in quiet mode."""
        mock_models = [
            {"name": "gemma3:latest", "size": 5368709120},
            {"name": "llava:latest", "size": 4294967296},
        ]

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_models

            result = runner.invoke(app, ["list", "--quiet"])

            assert result.exit_code == 0
            lines = result.output.strip().split("\n")
            assert len(lines) == 2
            assert "gemma3:latest" in lines[0]
            assert "llava:latest" in lines[1]

    def test_list_models_empty(self) -> None:
        """Should show empty message when no models installed."""
        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 0
            assert "Nenhum modelo instalado" in result.output

    def test_list_models_connection_error(self) -> None:
        """Should show friendly error when Ollama offline."""
        from miru.ollama.client import OllamaConnectionError

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = OllamaConnectionError("Cannot connect")

            result = runner.invoke(app, ["list"])

            assert result.exit_code == 1
            assert "Não foi possível conectar" in result.output
            assert "ollama serve" in result.output

    def test_list_models_json_quiet_pipeable(self) -> None:
        """Should output JSON compatible with jq in quiet mode."""
        mock_models = [
            {"name": "model1:latest", "size": 1000000000},
            {"name": "model2:latest", "size": 2000000000},
        ]

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_models

            result = runner.invoke(app, ["list", "--format", "json", "--quiet"])

            assert result.exit_code == 0
            # Should be valid JSON
            output = json.loads(result.output.strip())
            assert isinstance(output, list)
            assert len(output) == 2

    def test_list_models_custom_host(self) -> None:
        """Should use custom host when provided."""
        mock_models = []

        with patch("miru.commands.list._list_models_async", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_models

            result = runner.invoke(app, ["list", "--host", "http://custom:11434"])

            assert result.exit_code == 0
            # Verify the custom host was passed
            call_args = mock_list.call_args[0]
            assert "custom" in call_args[0]