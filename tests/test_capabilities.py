"""Tests for miru/model/capabilities.py."""

from unittest.mock import AsyncMock, patch

import pytest

from miru.model.capabilities import ModelCapabilities, _extract_num_ctx, get_capabilities
from miru.ollama.client import OllamaClient


class TestExtractNumCtx:
    """Tests for _extract_num_ctx helper function."""

    def test_extract_num_ctx_found(self) -> None:
        """Should extract num_ctx from parameters string."""
        parameters = "num_ctx\t4096\nnum_batch\t512\n"
        result = _extract_num_ctx(parameters)
        assert result == 4096

    def test_extract_num_ctx_not_found(self) -> None:
        """Should return None when num_ctx not in parameters."""
        parameters = "num_batch\t512\n"
        result = _extract_num_ctx(parameters)
        assert result is None

    def test_extract_num_ctx_empty_string(self) -> None:
        """Should return None for empty string."""
        result = _extract_num_ctx("")
        assert result is None

    def test_extract_num_ctx_invalid_value(self) -> None:
        """Should return None when num_ctx value is not an int."""
        parameters = "num_ctx\tinvalid\n"
        result = _extract_num_ctx(parameters)
        assert result is None


class TestGetCapabilities:
    """Tests for get_capabilities function."""

    @pytest.mark.asyncio
    async def test_vision_model_with_clip(self) -> None:
        """Should detect vision capability when clip in families."""
        mock_response = {
            "details": {
                "families": ["llama", "clip"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "modelinfo": {"llm.context_length": 4096},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "llava:latest")

            assert caps.supports_vision is True
            assert "clip" in caps.families
            assert caps.max_context == 4096
            assert caps.parameter_size == "7B"
            assert caps.quantization == "Q4_K_M"

    @pytest.mark.asyncio
    async def test_non_vision_model_without_clip(self) -> None:
        """Should not detect vision when clip not in families."""
        mock_response = {
            "details": {
                "families": ["llama"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
            "modelinfo": {},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:latest")

            assert caps.supports_vision is False
            assert caps.families == ["llama"]

    @pytest.mark.asyncio
    async def test_missing_families_key(self) -> None:
        """Should not raise exception when families key is absent."""
        mock_response = {
            "details": {},
            "modelinfo": {},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "unknown-model")

            assert caps.supports_vision is False
            assert caps.families == []

    @pytest.mark.asyncio
    async def test_none_families_value(self) -> None:
        """Should handle None families value (some models return None instead of [])."""
        mock_response = {
            "details": {"families": None, "parameter_size": "7B"},
            "modelinfo": {},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "glm-5:cloud")

            assert caps.supports_vision is False
            assert caps.families == []

    @pytest.mark.asyncio
    async def test_vision_capability_from_capabilities_field(self) -> None:
        """Should detect vision from capabilities field (cloud models)."""
        mock_response = {
            "details": {"families": None, "parameter_size": "27B"},
            "model_info": {"gemma3.context_length": 131072},
            "capabilities": ["completion", "vision"],
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:27b-cloud")

            assert caps.supports_vision is True
            assert caps.max_context == 131072

    @pytest.mark.asyncio
    async def test_architecture_specific_context_length(self) -> None:
        """Should detect context length from architecture-specific field."""
        mock_response = {
            "details": {"families": [], "parameter_size": "27B"},
            "model_info": {"gemma3.context_length": 131072, "general.architecture": "gemma3"},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:27b")

            assert caps.max_context == 131072

    @pytest.mark.asyncio
    async def test_none_capabilities_field(self) -> None:
        """Should handle None capabilities value."""
        mock_response = {
            "details": {"families": None, "parameter_size": "7B"},
            "model_info": {},
            "capabilities": None,
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "test-model")

            assert caps.supports_vision is False

    @pytest.mark.asyncio
    async def test_max_context_from_modelinfo(self) -> None:
        """Should read max_context from modelinfo.llm.context_length."""
        mock_response = {
            "details": {"families": [], "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            "modelinfo": {"llm.context_length": 8192},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:latest")

            assert caps.max_context == 8192

    @pytest.mark.asyncio
    async def test_max_context_from_parameters(self) -> None:
        """Should read max_context from parameters when modelinfo absent."""
        mock_response = {
            "details": {"families": [], "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            "modelinfo": {},
            "parameters": "num_ctx\t4096\nnum_batch\t512\n",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:latest")

            assert caps.max_context == 4096

    @pytest.mark.asyncio
    async def test_max_context_default(self) -> None:
        """Should use default 2048 when neither source has num_ctx."""
        mock_response = {
            "details": {"families": [], "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            "modelinfo": {},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:latest")

            assert caps.max_context == 2048

    @pytest.mark.asyncio
    async def test_max_context_modelinfo_takes_precedence(self) -> None:
        """modelinfo should take precedence over parameters."""
        mock_response = {
            "details": {"families": [], "parameter_size": "7B", "quantization_level": "Q4_K_M"},
            "modelinfo": {"llm.context_length": 8192},
            "parameters": "num_ctx\t2048\n",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "gemma3:latest")

            assert caps.max_context == 8192

    @pytest.mark.asyncio
    async def test_missing_details_uses_defaults(self) -> None:
        """Should handle missing details gracefully."""
        mock_response = {
            "modelinfo": {},
            "parameters": "",
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "show_model", new_callable=AsyncMock) as mock_show:
            mock_show.return_value = mock_response

            async with client:
                caps = await get_capabilities(client, "unknown-model")

            assert caps.supports_vision is False
            assert caps.families == []
            assert caps.parameter_size == "unknown"
            assert caps.quantization == "unknown"


class TestModelCapabilities:
    """Tests for ModelCapabilities dataclass."""

    def test_dataclass_creation(self) -> None:
        """Should create ModelCapabilities instance."""
        caps = ModelCapabilities(
            supports_vision=True,
            max_context=4096,
            families=["llama", "clip"],
            parameter_size="7B",
            quantization="Q4_K_M",
        )

        assert caps.supports_vision is True
        assert caps.max_context == 4096
        assert caps.families == ["llama", "clip"]
        assert caps.parameter_size == "7B"
        assert caps.quantization == "Q4_K_M"

    def test_dataclass_repr(self) -> None:
        """Should have proper repr."""
        caps = ModelCapabilities(
            supports_vision=False,
            max_context=2048,
            families=["llama"],
            parameter_size="13B",
            quantization="Q5_K_M",
        )
        assert "supports_vision=False" in repr(caps)
