"""Tests for miru/commands/info.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from miru.cli import app
from miru.model.capabilities import ModelCapabilities
from miru.ollama.client import OllamaConnectionError, OllamaModelNotFound

runner = CliRunner()


class TestInfoCommand:
    """Tests for miru info command."""

    def test_info_text_format(self) -> None:
        """Should display model info in panel format."""
        mock_model_data = {
            "details": {
                "families": ["llama", "clip"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "parameters": "temperature\t0.8\nnum_ctx\t4096\n",
        }
        mock_capabilities = {
            "supports_vision": True,
            "max_context": 4096,
            "families": ["llama", "clip"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "llava:latest"])

            assert result.exit_code == 0
            assert "llava:latest" in result.output
            assert "llama, clip" in result.output
            assert "Suporte a imagens" in result.output

    def test_info_vision_capability_true(self) -> None:
        """Should show vision support as 'sim' for models with clip."""
        mock_model_data = {
            "details": {
                "families": ["llama", "clip"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "parameters": "",
        }
        mock_capabilities = {
            "supports_vision": True,
            "max_context": 4096,
            "families": ["llama", "clip"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "llava"])

            assert result.exit_code == 0
            assert "sim" in result.output.lower()

    def test_info_vision_capability_false(self) -> None:
        """Should show vision support as 'não' for models without clip."""
        mock_model_data = {
            "details": {
                "families": ["llama"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "parameters": "",
        }
        mock_capabilities = {
            "supports_vision": False,
            "max_context": 2048,
            "families": ["llama"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "gemma3"])

            assert result.exit_code == 0
            assert "não" in result.output.lower()

    def test_info_json_format(self) -> None:
        """Should output valid JSON with --format json."""
        mock_model_data = {
            "details": {
                "families": ["llama"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "parameters": "temperature\t0.8\n",
        }
        mock_capabilities = {
            "supports_vision": False,
            "max_context": 2048,
            "families": ["llama"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "gemma3", "--format", "json"])

            assert result.exit_code == 0
            output = json.loads(result.output.strip())
            assert "capabilities" in output
            assert output["capabilities"]["supports_vision"] is False

    def test_info_quiet_mode(self) -> None:
        """Should output minimal info in quiet mode."""
        mock_model_data = {
            "details": {"families": ["llama"]},
            "parameters": "",
        }
        mock_capabilities = {
            "supports_vision": False,
            "max_context": 2048,
            "families": ["llama"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "gemma3", "--quiet"])

            assert result.exit_code == 0
            assert "gemma3" in result.output

    def test_info_model_not_found(self) -> None:
        """Should show error message when model not found."""
        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.side_effect = OllamaModelNotFound("model not found")

            result = runner.invoke(app, ["info", "unknown-model"])

            assert result.exit_code == 1
            assert "não encontrado" in result.output
            assert "miru list" in result.output

    def test_info_connection_error(self) -> None:
        """Should show friendly error when Ollama offline."""
        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.side_effect = OllamaConnectionError("Cannot connect")

            result = runner.invoke(app, ["info", "gemma3"])

            assert result.exit_code == 1
            assert "Não foi possível conectar" in result.output
            assert "ollama serve" in result.output

    def test_info_with_parameters(self) -> None:
        """Should display model parameters in table format."""
        mock_model_data = {
            "details": {
                "families": ["llama"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "parameters": "temperature\t0.8\ntop_p\t0.9\ntop_k\t40\nnum_ctx\t4096\n",
        }
        mock_capabilities = {
            "supports_vision": False,
            "max_context": 4096,
            "families": ["llama"],
            "parameter_size": "7B",
            "quantization": "Q4_K_M",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "gemma3"])

            assert result.exit_code == 0
            assert "temperature" in result.output
            assert "top_p" in result.output
            assert "top_k" in result.output

    def test_info_custom_host(self) -> None:
        """Should use custom host when provided."""
        mock_model_data = {"details": {}, "parameters": ""}
        mock_capabilities = {
            "supports_vision": False,
            "max_context": 2048,
            "families": [],
            "parameter_size": "unknown",
            "quantization": "unknown",
        }

        with patch("miru.commands.info._get_model_info_async", new_callable=AsyncMock) as mock_info:
            mock_info.return_value = (mock_model_data, mock_capabilities)

            result = runner.invoke(app, ["info", "gemma3", "--host", "http://custom:11434"])

            assert result.exit_code == 0
            call_args = mock_info.call_args[0]
            assert "custom" in call_args[0]