"""Tests for miru/commands/copy.py."""

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from miru.cli import app
from miru.ollama.client import OllamaConnectionError, OllamaModelNotFound

runner = CliRunner()


class TestCopyCommand:
    """Tests for miru copy command."""

    def test_copy_existing_model_to_new_name(self) -> None:
        """Should copy model to new name."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[
                    {"name": "gemma3:latest", "size": 4000000000},
                ]
            )
            client.copy_model = AsyncMock(return_value={"status": "copying"})
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "gemma3:latest", "gemma3-backup"])

            assert result.exit_code == 0
            assert "Copiado" in result.output
            client.copy_model.assert_called_once_with("gemma3:latest", "gemma3-backup")

    def test_copy_nonexistent_source_model(self) -> None:
        """Should show error when source model does not exist."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(return_value=[])
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "nonexistent", "new-name"])

            assert result.exit_code == 1
            assert "não encontrado" in result.output

    def test_copy_destination_already_exists_without_force(self) -> None:
        """Should show error when destination exists and --force not used."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[
                    {"name": "gemma3:latest", "size": 4000000000},
                    {"name": "backup", "size": 4000000000},
                ]
            )
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "gemma3:latest", "backup"])

            assert result.exit_code == 1
            assert "já existe" in result.output

    def test_copy_destination_already_exists_with_force(self) -> None:
        """Should overwrite when destination exists and --force is used."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[
                    {"name": "gemma3:latest", "size": 4000000000},
                    {"name": "backup", "size": 4000000000},
                ]
            )
            client.copy_model = AsyncMock(return_value={"status": "copying"})
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "gemma3:latest", "backup", "--force"])

            assert result.exit_code == 0
            assert "Copiado" in result.output

    def test_copy_connection_error(self) -> None:
        """Should show friendly error when Ollama offline."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("Cannot connect"))
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "source", "dest"])

            assert result.exit_code == 1
            assert "Cannot connect" in result.output

    def test_copy_shows_model_size(self) -> None:
        """Should show model size after successful copy."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)

            # First call returns source, second call returns both (including backup)
            client.list_models = AsyncMock(
                side_effect=[
                    [{"name": "gemma3:latest", "size": 4000000000}],  # Before copy
                    [
                        {"name": "gemma3:latest", "size": 4000000000},
                        {"name": "backup", "size": 4000000000},
                    ],  # After copy
                ]
            )
            client.copy_model = AsyncMock(return_value={"status": "copying"})
            MockClient.return_value = client

            result = runner.invoke(app, ["copy", "gemma3:latest", "backup"])

            assert result.exit_code == 0
            assert "3.73 GB" in result.output

    def test_copy_custom_host(self) -> None:
        """Should use custom host when provided."""
        with patch("miru.commands.copy.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(return_value=[{"name": "test-model", "size": 1000000}])
            client.copy_model = AsyncMock(return_value={"status": "copying"})
            MockClient.return_value = client

            result = runner.invoke(
                app, ["copy", "test-model", "backup", "--host", "http://custom:11434"]
            )

            assert result.exit_code == 0
            MockClient.assert_called_once_with("http://custom:11434")
