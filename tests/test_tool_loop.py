"""Tests for miru/tool_integration.py — execute_tool_loop core."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.tool_integration import execute_tool_loop


def _chunk_with_tool_call():
    return {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": "read_file", "arguments": {"path": "x.txt"}}}
            ],
        }
    }


def _chunk_final(text="resposta final"):
    return {"message": {"content": text}, "done": True}


class TestExecuteToolLoop:
    @pytest.mark.asyncio
    async def test_final_response_without_tools(self) -> None:
        client = MagicMock()

        async def gen():
            yield _chunk_final()

        client.chat_with_tools = MagicMock(return_value=gen())
        tool_manager = MagicMock()
        tool_manager.get_tool_definitions.return_value = []
        tool_manager.execute_tool.return_value = ("r", None)

        result = await execute_tool_loop(
            client, "m", [{"role": "user", "content": "q"}], tool_manager,
            {}, quiet=True, max_iterations=3,
        )
        assert "resposta final" in result

    @pytest.mark.asyncio
    async def test_tool_call_then_final(self) -> None:
        client = MagicMock()

        def tool_gen():
            async def gen():
                yield _chunk_with_tool_call()

            return gen()

        def final_gen():
            async def gen():
                yield _chunk_final("depois da tool")

            return gen()

        calls = {"n": 0}

        def side_effect(*a, **k):
            calls["n"] += 1
            return tool_gen() if calls["n"] == 1 else final_gen()

        client.chat_with_tools = MagicMock(side_effect=side_effect)
        tool_manager = MagicMock()
        tool_manager.get_tool_definitions.return_value = []
        tool_manager.execute_tool.return_value = ("conteúdo do arquivo", None)

        messages = [{"role": "user", "content": "q"}]
        result = await execute_tool_loop(
            client, "m", messages, tool_manager, {}, quiet=True, max_iterations=3,
        )
        assert "depois da tool" in result
        # tool result appended to messages
        assert any(m.get("role") == "tool" for m in messages)

    @pytest.mark.asyncio
    async def test_iteration_limit(self) -> None:
        client = MagicMock()

        def tool_only_gen():
            async def gen():
                yield _chunk_with_tool_call()
                # generator ENDS so the outer loop can advance to next iteration

            return gen()

        # fresh generator per chat_with_tools call
        client.chat_with_tools = MagicMock(side_effect=lambda *a, **k: tool_only_gen())
        tool_manager = MagicMock()
        tool_manager.get_tool_definitions.return_value = []
        tool_manager.execute_tool.return_value = ("r", None)

        result = await execute_tool_loop(
            client, "m", [{"role": "user", "content": "q"}], tool_manager,
            {}, quiet=True, max_iterations=2,
        )
        assert result == ""
