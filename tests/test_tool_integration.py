"""Tests for miru/tool_integration.py — tool manager setup and tool loops."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.tool_integration import (
    create_tool_manager,
    enhance_tavily_search,
    generate_query_variations,
    process_tool_calls,
    validate_tools_config,
)
from miru.tools import ToolExecutionMode


class TestCreateToolManager:
    def test_disabled_returns_none(self) -> None:
        assert create_tool_manager(enable_tools=False, enable_tavily=False) is None

    def test_creates_manager_with_default_mode(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value=None):
            manager = create_tool_manager(enable_tools=True)
        assert manager is not None
        assert manager.mode == ToolExecutionMode.AUTO_SAFE

    def test_manual_mode(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value=None):
            manager = create_tool_manager(enable_tools=True, tool_mode="manual")
        assert manager.mode == ToolExecutionMode.MANUAL

    def test_unknown_mode_falls_back(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value=None):
            manager = create_tool_manager(enable_tools=True, tool_mode="bogus")
        assert manager.mode == ToolExecutionMode.AUTO_SAFE

    def test_tavily_api_key_passed(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value="tvly-abc"):
            manager = create_tool_manager(enable_tavily=True)
        assert manager is not None
        assert manager.tavily_api_key == "tvly-abc"


class TestValidateToolsConfig:
    def test_both_disabled_ok(self) -> None:
        validate_tools_config(False, False)  # no raise

    def test_tavily_without_key_exits(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value=None):
            with pytest.raises(SystemExit) as exc:
                validate_tools_config(True, False)
        assert exc.value.code == 1

    def test_tavily_with_key_ok(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value="tvly-key"):
            validate_tools_config(True, False)

    def test_enable_tools_alone_ok(self) -> None:
        with patch("miru.tool_integration.get_config_value", return_value=None):
            validate_tools_config(False, True)


class TestProcessToolCalls:
    @pytest.mark.asyncio
    async def test_appends_tool_result(self) -> None:
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = ("result", None)
        messages: list[dict] = [{"role": "user", "content": "q"}]
        updated = await process_tool_calls(
            client=MagicMock(), model="m", messages=messages,
            tool_calls=[{"name": "read_file", "arguments": {"path": "/x"}}],
            tool_manager=tool_manager,
        )
        assert len(updated) == 2
        assert updated[1]["role"] == "tool"


class TestGenerateQueryVariations:
    @pytest.mark.asyncio
    async def test_returns_original_on_exception(self) -> None:
        client = MagicMock()
        client.chat.side_effect = RuntimeError("boom")
        variations = await generate_query_variations(client, "m", "python decorators")
        assert variations == ["python decorators"]

    @pytest.mark.asyncio
    async def test_parses_variations_from_response(self) -> None:
        client = MagicMock()
        chunks = [
            {"message": {"content": "Python decorators tutorial\n- how do they work\n* common patterns"}}
        ]
        client.chat.return_value = _async_iter(chunks)
        variations = await generate_query_variations(client, "m", "python decorators", max_variations=2)
        assert variations[0] == "python decorators"
        assert len(variations) >= 2

    @pytest.mark.asyncio
    async def test_strips_numbering_prefixes(self) -> None:
        client = MagicMock()
        chunks = [{"message": {"content": "1. first variation\n2. second variation"}}]
        client.chat.return_value = _async_iter(chunks)
        variations = await generate_query_variations(client, "m", "q", max_variations=3)
        assert "first variation" in variations
        assert "second variation" in variations


class TestEnhanceTavilySearch:
    @pytest.mark.asyncio
    async def test_returns_error_from_tool(self) -> None:
        client = MagicMock()
        client.chat.side_effect = RuntimeError("no model")
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = (None, ValueError("failed"))
        result, error = await enhance_tavily_search(client, "m", "query", tool_manager)
        assert result == ""
        assert error is not None

    @pytest.mark.asyncio
    async def test_combines_results(self) -> None:
        client = MagicMock()
        client.chat.side_effect = RuntimeError("no model")
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = ("result-a", None)
        result, error = await enhance_tavily_search(client, "m", "query", tool_manager)
        assert "result-a" in result
        assert error is None


def _async_iter(items):
    async def gen():
        for i in items:
            yield i

    return gen()
