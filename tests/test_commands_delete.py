"""Tests for miru/commands/delete.py."""

from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from miru.cli import app
from miru.ollama.client import OllamaConnectionError, OllamaModelNotFound

runner = CliRunner()


class TestDeleteCommand:
    """Tests for miru delete command."""

    def test_delete_existing_model_with_force(self) -> None:
        """Should delete model without confirmation when --force is used."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[{"name": "gemma3:latest", "size": 1000000}]
            )
            client.delete_model = AsyncMock(return_value={})
            MockClient.return_value = client

            result = runner.invoke(app, ["delete", "gemma3:latest", "--force"])

            assert result.exit_code == 0
            assert "deletado com sucesso" in result.output
            client.delete_model.assert_called_once_with("gemma3:latest")

    def test_delete_nonexistent_model(self) -> None:
        """Should show error when trying to delete non-existent model."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(return_value=[])
            MockClient.return_value = client

            result = runner.invoke(app, ["delete", "nonexistent-model"])

            assert result.exit_code == 1
            assert "não encontrado" in result.output

    def test_delete_connection_error(self) -> None:
        """Should show friendly error when Ollama offline."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("Cannot connect"))
            MockClient.return_value = client

            result = runner.invoke(app, ["delete", "gemma3:latest", "--force"])

            assert result.exit_code == 1
            assert "Cannot connect" in result.output

    def test_delete_cancel_confirmation(self) -> None:
        """Should cancel when user declines confirmation."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[{"name": "gemma3:latest", "size": 1000000}]
            )
            MockClient.return_value = client

            result = runner.invoke(app, ["delete", "gemma3:latest"], input="n\n")

            assert result.exit_code == 0
            assert "Cancelado" in result.output
            client.delete_model.assert_not_called()

    def test_delete_confirm_yes(self) -> None:
        """Should delete when user confirms."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(
                return_value=[{"name": "gemma3:latest", "size": 1000000}]
            )
            client.delete_model = AsyncMock(return_value={})
            MockClient.return_value = client

            result = runner.invoke(app, ["delete", "gemma3:latest"], input="y\n")

            assert result.exit_code == 0
            assert "deletado com sucesso" in result.output
            client.delete_model.assert_called_once_with("gemma3:latest")

    def test_delete_custom_host(self) -> None:
        """Should use custom host when provided."""
        with patch("miru.commands.delete.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.list_models = AsyncMock(return_value=[{"name": "test-model", "size": 1000000}])
            client.delete_model = AsyncMock(return_value={})
            MockClient.return_value = client

            result = runner.invoke(
                app, ["delete", "test-model", "--host", "http://custom:11434", "--force"]
            )

            assert result.exit_code == 0
            MockClient.assert_called_once_with("http://custom:11434")
