"""Tests for miru/ollama/client.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from miru.ollama.client import (
    DEFAULT_TIMEOUT,
    OllamaAPIError,
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFound,
)


class TestOllamaClientInit:
    """Tests for OllamaClient initialization."""

    def test_init_strips_trailing_slash(self) -> None:
        """Should strip trailing slash from host."""
        client = OllamaClient(host="http://localhost:11434/")
        assert client._host == "http://localhost:11434"

    def test_init_default_timeout(self) -> None:
        """Should have default timeout of 30s."""
        client = OllamaClient(host="http://localhost:11434")
        assert client._timeout == DEFAULT_TIMEOUT

    def test_init_custom_timeout(self) -> None:
        """Should accept custom timeout."""
        client = OllamaClient(host="http://localhost:11434", timeout=60.0)
        assert client._timeout == 60.0


class TestOllamaClientContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self) -> None:
        """Should create internal client on enter."""
        client = OllamaClient(host="http://localhost:11434")
        async with client as c:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
            assert c is client

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Should close internal client on exit."""
        client = OllamaClient(host="http://localhost:11434")
        async with client:
            internal_client = client._client
            assert internal_client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_context_manager_raises_without_context(self) -> None:
        """Should raise RuntimeError if used without context manager."""
        client = OllamaClient(host="http://localhost:11434")
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await client.list_models()


class TestOllamaClientListModels:
    """Tests for list_models method."""

    @pytest.mark.asyncio
    async def test_list_models_success(self) -> None:
        """Should return list of models."""
        mock_response = {
            "models": [
                {
                    "name": "gemma3:latest",
                    "size": 5368709120,
                    "modified_at": "2026-04-01T00:00:00Z",
                },
                {"name": "llava:latest", "size": 4294967296, "modified_at": "2026-04-02T00:00:00Z"},
            ]
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http_client = MagicMock(spec=httpx.AsyncClient)
            mock_get_client.return_value = mock_http_client

            with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response

                async with client:
                    result = await client.list_models()

            assert len(result) == 2
            assert result[0]["name"] == "gemma3:latest"

    @pytest.mark.asyncio
    async def test_list_models_empty(self) -> None:
        """Should return empty list when no models."""
        mock_response = {"models": []}

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with client:
                result = await client.list_models()

            assert result == []


class TestOllamaClientShowModel:
    """Tests for show_model method."""

    @pytest.mark.asyncio
    async def test_show_model_success(self) -> None:
        """Should return model details."""
        mock_response = {
            "license": "MIT",
            "modelfile": "FROM gemma3",
            "parameters": "num_ctx\t4096\n",
            "details": {
                "families": ["llama"],
                "parameter_size": "7B",
                "quantization_level": "Q4_K_M",
            },
        }

        client = OllamaClient(host="http://localhost:11434")

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with client:
                result = await client.show_model("gemma3:latest")

            assert result["details"]["families"] == ["llama"]


class TestOllamaClientGenerate:
    """Tests for generate method."""

    @pytest.mark.asyncio
    async def test_generate_streaming(self) -> None:
        """Should yield chunks incrementally."""
        chunks = [
            {"response": "Hello", "done": False},
            {"response": " world", "done": False},
            {"response": "", "done": True, "eval_count": 10, "eval_duration": 1000000000},
        ]

        lines = [json.dumps(chunk) for chunk in chunks]

        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock()

        async def async_iter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.stream = MagicMock()

        async def mock_stream(*args, **kwargs):
            mock_response.raise_for_status()
            return mock_response

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        mock_http_client.stream.return_value = stream_context()

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                results = []
                async for chunk in client.generate(
                    model="gemma3:latest",
                    prompt="Hello",
                ):
                    results.append(chunk)

            assert len(results) == 3
            assert results[0]["response"] == "Hello"
            assert results[-1]["done"] is True

    @pytest.mark.asyncio
    async def test_generate_with_images(self) -> None:
        """Should include images in request body."""
        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock()

        async def async_iter_lines():
            yield json.dumps({"response": "test", "done": True})

        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        captured_body = None

        def capture_body(method, url, json):
            nonlocal captured_body
            captured_body = json
            return stream_context()

        mock_http_client.stream = capture_body

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                async for _ in client.generate(
                    model="llava:latest",
                    prompt="What's in this image?",
                    images=["base64imagedata"],
                ):
                    pass

        assert captured_body is not None
        assert "images" in captured_body
        assert captured_body["images"] == ["base64imagedata"]

    @pytest.mark.asyncio
    async def test_generate_with_options_filters_none(self) -> None:
        """Should filter None values from options."""
        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            yield json.dumps({"response": "", "done": True})

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        captured_body = None

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        def capture_body(method, url, json):
            nonlocal captured_body
            captured_body = json
            return stream_context()

        mock_http_client.stream = capture_body

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                async for _ in client.generate(
                    model="gemma3:latest",
                    prompt="test",
                    options={"temperature": 0.7, "num_predict": None},
                ):
                    pass

        assert captured_body is not None
        assert "temperature" in captured_body["options"]
        assert "num_predict" not in captured_body["options"]

    @pytest.mark.asyncio
    async def test_generate_without_options(self) -> None:
        """Should not include options key when None."""
        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            yield json.dumps({"response": "", "done": True})

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        captured_body = None

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        def capture_body(method, url, json):
            nonlocal captured_body
            captured_body = json
            return stream_context()

        mock_http_client.stream = capture_body

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                async for _ in client.generate(
                    model="gemma3:latest",
                    prompt="test",
                ):
                    pass

        assert captured_body is not None
        assert "options" not in captured_body


class TestOllamaClientChat:
    """Tests for chat method."""

    @pytest.mark.asyncio
    async def test_chat_streaming(self) -> None:
        """Should yield chat chunks incrementally."""
        chunks = [
            {"message": {"role": "assistant", "content": "Hi"}, "done": False},
            {"message": {"role": "assistant", "content": " there"}, "done": False},
            {"done": True},
        ]

        lines = [json.dumps(chunk) for chunk in chunks]

        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock()

        async def async_iter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        mock_http_client.stream.return_value = stream_context()

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                results = []
                messages = [{"role": "user", "content": "Hello"}]
                async for chunk in client.chat("gemma3:latest", messages):
                    results.append(chunk)

            assert len(results) == 3
            assert results[0]["message"]["content"] == "Hi"

    @pytest.mark.asyncio
    async def test_chat_with_options(self) -> None:
        """Should include options in chat request."""
        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            yield json.dumps({"done": True})

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        captured_body = None

        def capture_body(method, url, **kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("json")
            return stream_context()

        mock_http_client.stream = capture_body

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                messages = [{"role": "user", "content": "test"}]
                async for _ in client.chat(
                    "gemma3:latest",
                    messages,
                    options={"temperature": 0.5},
                ):
                    pass

        assert captured_body is not None
        assert captured_body["options"]["temperature"] == 0.5


class TestOllamaClientPull:
    """Tests for pull method."""

    @pytest.mark.asyncio
    async def test_pull_progress(self) -> None:
        """Should yield pull progress chunks."""
        chunks = [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 50, "total": 100},
            {"status": "success"},
        ]

        client = OllamaClient(host="http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            for chunk in chunks:
                yield json.dumps(chunk)

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock(spec=httpx.AsyncClient)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        mock_http_client.stream.return_value = stream_context()

        with patch("miru.ollama.client.httpx.AsyncClient", return_value=mock_http_client):
            with patch.object(client, "_get_client", return_value=mock_http_client):
                async with client:
                    results = []
                    async for chunk in client.pull("gemma3:latest"):
                        results.append(chunk)

                    assert len(results) == 3
                    assert results[0]["status"] == "pulling manifest"
                    assert results[1]["completed"] == 50


class TestOllamaClientErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        """Should raise OllamaConnectionError on ConnectError."""
        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaConnectionError, match="Cannot connect"):
                    await client.list_models()

    @pytest.mark.asyncio
    async def test_connection_timeout(self) -> None:
        """Should raise OllamaConnectionError on ConnectTimeout."""
        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=httpx.ConnectTimeout("Timeout"))

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaConnectionError, match="Connection timeout"):
                    await client.list_models()

    @pytest.mark.asyncio
    async def test_model_not_found(self) -> None:
        """Should raise OllamaModelNotFound on 404."""
        client = OllamaClient(host="http://localhost:11434")

        response = MagicMock()
        response.status_code = 404
        response.json = MagicMock(return_value={"error": "model not found"})
        response.text = "model not found"

        http_error = httpx.HTTPStatusError("404", request=MagicMock(), response=response)

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=http_error)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaModelNotFound, match="model not found"):
                    await client.list_models()

    @pytest.mark.asyncio
    async def test_api_error(self) -> None:
        """Should raise OllamaAPIError on other HTTP errors."""
        client = OllamaClient(host="http://localhost:11434")

        response = MagicMock()
        response.status_code = 500
        response.json = MagicMock(return_value={"error": "internal server error"})
        response.text = "internal server error"

        http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=response)

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=http_error)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaAPIError) as exc_info:
                    await client.list_models()

                assert exc_info.value.status_code == 500
                assert "internal server error" in exc_info.value.message


class TestDeleteModel:
    """Tests for delete_model method."""

    @pytest.mark.asyncio
    async def test_delete_model_success(self) -> None:
        """Should delete model successfully."""
        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(return_value=MagicMock(json=lambda: {}))

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                result = await client.delete_model("gemma3:latest")

                assert result == {}
                mock_http_client.request.assert_called_once_with(
                    "DELETE", "http://localhost:11434/api/delete", json={"model": "gemma3:latest"}
                )

    @pytest.mark.asyncio
    async def test_delete_model_not_found(self) -> None:
        """Should raise OllamaModelNotFound when model does not exist."""
        client = OllamaClient(host="http://localhost:11434")

        response = MagicMock()
        response.status_code = 404
        response.json = MagicMock(return_value={"error": "model not found"})
        response.text = "model not found"

        http_error = httpx.HTTPStatusError("404", request=MagicMock(), response=response)

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=http_error)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaModelNotFound, match="model not found"):
                    await client.delete_model("nonexistent")


class TestCopyModel:
    """Tests for copy_model method."""

    @pytest.mark.asyncio
    async def test_copy_model_success(self) -> None:
        """Should copy model successfully."""
        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=MagicMock(json=lambda: {"status": "copying"})
        )

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                result = await client.copy_model("gemma3:latest", "backup")

                assert result == {"status": "copying"}
                mock_http_client.request.assert_called_once_with(
                    "POST",
                    "http://localhost:11434/api/copy",
                    json={"source": "gemma3:latest", "destination": "backup"},
                )

    @pytest.mark.asyncio
    async def test_copy_model_not_found(self) -> None:
        """Should raise OllamaModelNotFound when source model does not exist."""
        client = OllamaClient(host="http://localhost:11434")

        response = MagicMock()
        response.status_code = 404
        response.json = MagicMock(return_value={"error": "model not found"})
        response.text = "model not found"

        http_error = httpx.HTTPStatusError("404", request=MagicMock(), response=response)

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(side_effect=http_error)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                with pytest.raises(OllamaModelNotFound, match="model not found"):
                    await client.copy_model("nonexistent", "backup")


class TestOllamaAPIError:
    """Tests for OllamaAPIError exception."""

    def test_api_error_message(self) -> None:
        """Should format status code and message."""
        error = OllamaAPIError(404, "not found")
        assert error.status_code == 404
        assert error.message == "not found"
        assert "[404] not found" in str(error)
