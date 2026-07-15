"""Tests for OllamaClient.chat_with_tools method."""

import json
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from miru.ollama.client import OllamaClient


class TestChatWithTools:
    """Tests for chat_with_tools method."""

    @pytest.mark.asyncio
    async def test_chat_with_tools_no_tools(self) -> None:
        """Test chat_with_tools without tools."""
        chunks = [
            {"message": {"role": "assistant", "content": "Hello"}, "done": False},
            {"message": {"role": "assistant", "content": ""}, "done": True},
        ]

        client = OllamaClient("http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            for chunk in chunks:
                yield json.dumps(chunk)

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock()

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            yield mock_response

        mock_http_client.stream.return_value = stream_context()

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                results = []
                async for chunk in client.chat_with_tools(
                    "test-model", [{"role": "user", "content": "Hi"}]
                ):
                    results.append(chunk)

                assert len(results) == 2
                assert results[0]["message"]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_chat_with_tools_with_tool_definition(self) -> None:
        """Test chat_with_tools with tool definitions."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string", "description": "City name"}},
                        "required": ["city"],
                    },
                },
            }
        ]

        chunks = [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_weather",
                                "arguments": {"city": "Tokyo"},
                            }
                        }
                    ],
                },
                "done": False,
            },
            {"message": {"role": "assistant", "content": ""}, "done": True},
        ]

        client = OllamaClient("http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            for chunk in chunks:
                yield json.dumps(chunk)

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock()

        captured_body = None

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("json")
            yield mock_response

        def capture_stream(*args, **kwargs):
            return stream_context(*args, **kwargs)

        mock_http_client.stream = capture_stream

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                results = []
                async for chunk in client.chat_with_tools(
                    "test-model",
                    [{"role": "user", "content": "Weather in Tokyo?"}],
                    tools=tools,
                ):
                    results.append(chunk)

                assert captured_body is not None
                assert "tools" in captured_body
                assert captured_body["tools"] == tools
                assert len(results) == 2
                assert "tool_calls" in results[0]["message"]

    @pytest.mark.asyncio
    async def test_chat_with_tools_with_options(self) -> None:
        """Test chat_with_tools with options."""
        chunks = [{"message": {"role": "assistant", "content": "Response"}, "done": True}]

        client = OllamaClient("http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            for chunk in chunks:
                yield json.dumps(chunk)

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock()

        captured_body = None

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("json")
            yield mock_response

        def capture_stream(*args, **kwargs):
            return stream_context(*args, **kwargs)

        mock_http_client.stream = capture_stream

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                async for chunk in client.chat_with_tools(
                    "test-model",
                    [{"role": "user", "content": "Hi"}],
                    options={"temperature": 0.7, "seed": 42},
                ):
                    pass

                assert captured_body is not None
                assert "options" in captured_body
                assert captured_body["options"]["temperature"] == 0.7
                assert captured_body["options"]["seed"] == 42

    @pytest.mark.asyncio
    async def test_chat_with_tools_streaming_messages_with_tool_history(self) -> None:
        """Test chat_with_tools accepts messages with tool_call history."""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": {"city": "Tokyo"},
                        }
                    }
                ],
            },
            {"role": "tool", "content": "15°C, sunny", "tool_name": "get_weather"},
        ]

        chunks = [
            {
                "message": {
                    "role": "assistant",
                    "content": "The weather in Tokyo is 15°C and sunny.",
                },
                "done": True,
            }
        ]

        client = OllamaClient("http://localhost:11434")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def async_iter_lines():
            for chunk in chunks:
                yield json.dumps(chunk)

        mock_response.aiter_lines = MagicMock()
        mock_response.aiter_lines.return_value = async_iter_lines()

        mock_http_client = MagicMock()

        captured_body = None

        @asynccontextmanager
        async def stream_context(*args, **kwargs):
            nonlocal captured_body
            captured_body = kwargs.get("json")
            yield mock_response

        def capture_stream(*args, **kwargs):
            return stream_context(*args, **kwargs)

        mock_http_client.stream = capture_stream

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                results = []
                async for chunk in client.chat_with_tools("test-model", messages):
                    results.append(chunk)

                assert captured_body is not None
                assert len(captured_body["messages"]) == 3
                assert captured_body["messages"][1]["tool_calls"] is not None
                assert captured_body["messages"][2]["role"] == "tool"
                assert len(results) == 1
