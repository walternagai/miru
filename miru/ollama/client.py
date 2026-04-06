"""Async HTTP client for Ollama API."""

import json
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx


class OllamaConnectionError(Exception):
    """Ollama server is not accessible."""


class OllamaModelNotFound(Exception):
    """Requested model not found."""


class OllamaAPIError(Exception):
    """Generic Ollama API error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")


DEFAULT_TIMEOUT = 30.0
PULL_TIMEOUT = 300.0


class OllamaClient:
    """
    Async HTTP client for Ollama API.

    Usage:
        async with OllamaClient(host="http://localhost:11434") as client:
            models = await client.list_models()
    """

    def __init__(self, host: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Initialize Ollama client.

        Args:
            host: Base URL of Ollama server (e.g., http://localhost:11434)
            timeout: Default timeout in seconds for requests
        """
        self._host = host.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OllamaClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager and close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the internal client, raising if not initialized."""
        if not self._client:
            raise RuntimeError("OllamaClient must be used as async context manager")
        return self._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request and handle errors.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Arguments passed to httpx request

        Returns:
            Response JSON as dict

        Raises:
            OllamaConnectionError: If server is not accessible
            OllamaModelNotFound: If model not found (404)
            OllamaAPIError: For other HTTP errors
        """
        client = self._get_client()
        url = f"{self._host}{endpoint}"

        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama server at {self._host}") from e
        except httpx.ConnectTimeout as e:
            raise OllamaConnectionError(
                f"Connection timeout to Ollama server at {self._host}"
            ) from e
        except httpx.TimeoutException as e:
            raise OllamaConnectionError(f"Request timeout to Ollama server at {self._host}") from e
        except httpx.HTTPStatusError as e:
            response = e.response
            try:
                error_body = response.json()
                error_msg = error_body.get("error", response.text)
            except Exception:
                error_msg = response.text

            if response.status_code == 404:
                raise OllamaModelNotFound(error_msg) from e
            raise OllamaAPIError(response.status_code, error_msg) from e

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List all available models.

        Returns:
            List of model dicts with 'name', 'size', 'modified_at' keys
        """
        response = await self._request("GET", "/api/tags")
        return cast(list[dict[str, Any]], response.get("models", []))

    async def show_model(self, model: str) -> dict[str, Any]:
        """
        Get model details and capabilities.

        Args:
            model: Model name (e.g., "llava:latest")

        Returns:
            Complete model metadata dict
        """
        return await self._request("POST", "/api/show", json={"model": model})

    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
        options: dict[str, Any] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate text completion (streaming).

        Args:
            model: Model name
            prompt: Input prompt
            images: Optional list of base64-encoded images
            options: Optional generation parameters (temperature, num_predict, etc.)
            stream: Whether to stream response (must be True)

        Yields:
            Dict chunks with response text and metadata

        Example:
            async for chunk in client.generate("gemma3", "Hello"):
                print(chunk.get("response", ""), end="")
        """
        client = self._get_client()
        url = f"{self._host}/api/generate"

        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }

        if images:
            body["images"] = images

        if options:
            filtered_options = {k: v for k, v in options.items() if v is not None}
            if filtered_options:
                body["options"] = filtered_options

        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    chunk: dict[str, Any] = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, Any] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Chat completion with multi-turn conversation (streaming).

        Args:
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            options: Optional generation parameters
            stream: Whether to stream response (must be True)

        Yields:
            Dict chunks with response content

        Example:
            messages = [{"role": "user", "content": "Hello"}]
            async for chunk in client.chat("gemma3", messages):
                print(chunk.get("message", {}).get("content", ""), end="")
        """
        client = self._get_client()
        url = f"{self._host}/api/chat"

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        if options:
            filtered_options = {k: v for k, v in options.items() if v is not None}
            if filtered_options:
                body["options"] = filtered_options

        async with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    chunk: dict[str, Any] = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break

    async def pull(self, model: str) -> AsyncIterator[dict[str, Any]]:
        """
        Pull/download model from registry (streaming progress).

        Args:
            model: Model name to download

        Yields:
            Dict chunks with 'status', 'completed', 'total' fields
        """
        client = self._get_client()
        client_with_timeout = httpx.AsyncClient(timeout=PULL_TIMEOUT)

        url = f"{self._host}/api/pull"
        body = {"model": model, "stream": True}

        try:
            async with client_with_timeout.stream("POST", url, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        chunk: dict[str, Any] = json.loads(line)
                        yield chunk
        finally:
            await client_with_timeout.aclose()

    async def delete_model(self, model: str) -> dict[str, Any]:
        """
        Delete a model from local storage.

        Args:
            model: Model name to delete

        Returns:
            Empty dict on success

        Raises:
            OllamaModelNotFound: If model not found
        """
        return await self._request("DELETE", "/api/delete", json={"model": model})

    async def copy_model(self, source: str, destination: str) -> dict[str, Any]:
        """
        Copy/create a new model from an existing one.

        Args:
            source: Source model name
            destination: New model name

        Returns:
            Status message

        Raises:
            OllamaModelNotFound: If source model not found
        """
        return await self._request(
            "POST", "/api/copy", json={"source": source, "destination": destination}
        )

    async def embed(
        self,
        model: str,
        prompt: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate embedding vector for text.

        Args:
            model: Model name (e.g., "nomic-embed-text")
            prompt: Text to embed
            options: Optional generation parameters

        Returns:
            Dict with 'embedding' (list of floats) and metadata

        Example:
            result = await client.embed("nomic-embed-text", "Hello world")
            embedding = result["embedding"]  # [0.123, -0.456, ...]
        """
        body: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
        }

        if options:
            body["options"] = options

        return await self._request("POST", "/api/embeddings", json=body)
