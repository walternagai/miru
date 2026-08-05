"""Tests for miru/tools/execution.py — ToolExecutionManager modes."""

import warnings
from unittest.mock import patch

import pytest

from miru.tools.execution import ToolExecutionManager, ToolExecutionMode


def _manager(**kwargs):
    defaults = dict(
        mode=ToolExecutionMode.AUTO_SAFE,
        sandbox_dir=None,
    )
    defaults.update(kwargs)
    return ToolExecutionManager(**defaults)


class TestModes:
    def test_disabled_returns_no_definitions(self) -> None:
        m = _manager(mode=ToolExecutionMode.DISABLED)
        assert m.get_tool_definitions() == []
        assert m.is_tool_enabled() is False

    def test_enabled_has_definitions(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO_SAFE, sandbox_dir=".")
        assert m.is_tool_enabled() is True
        assert len(m.get_tool_definitions()) > 0

    def test_has_tools(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".")
        assert m.has_tools() is True


class TestShouldExecuteTool:
    def test_disabled(self) -> None:
        m = _manager(mode=ToolExecutionMode.DISABLED)
        ok, reason = m.should_execute_tool("read_file", {})
        assert ok is False
        assert "disabled" in reason

    def test_auto_executes(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".")
        ok, reason = m.should_execute_tool("read_file", {})
        assert ok is True
        assert reason is None

    def test_manual_requires_approval(self) -> None:
        m = _manager(mode=ToolExecutionMode.MANUAL, sandbox_dir=".")
        ok, reason = m.should_execute_tool("read_file", {})
        assert ok is False
        assert "approval" in reason

    def test_auto_safe_blocks_delete(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO_SAFE, sandbox_dir=".")
        ok, reason = m.should_execute_tool("delete_file", {"path": "x"})
        assert ok is False
        assert "Dangerous" in reason

    def test_auto_safe_allows_safe(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO_SAFE, sandbox_dir=".")
        ok, _ = m.should_execute_tool("read_file", {"path": "x"})
        assert ok is True


class TestExecuteTool:
    def test_execute_returns_result(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".")
        result, error = m.execute_tool("file_exists", {"path": "x"})
        assert error is None
        assert result is not None

    def test_execute_error(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".")
        result, error = m.execute_tool("nope_tool", {})
        assert result is None
        assert error is not None


class TestListTools:
    def test_list(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".")
        tools = m.list_tools()
        assert len(tools) > 0
        assert all("name" in t and "description" in t for t in tools)


class TestTavilyWarning:
    def test_tavily_error_warns(self) -> None:
        from miru.tools.tavily import TavilyError

        with patch("miru.tools.execution.create_tavily_tools", side_effect=TavilyError("no key")):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                _manager(mode=ToolExecutionMode.AUTO, sandbox_dir=".", enable_tavily=True)
        assert any("Tavily" in str(w.message) for w in caught)


class TestProcessToolCallsLoop:
    @pytest.mark.asyncio
    async def test_disabled_returns_messages(self) -> None:
        m = _manager(mode=ToolExecutionMode.DISABLED)
        msgs = [{"role": "user", "content": "q"}]
        result = await m.process_tool_calls_loop(msgs, chat_func=None)
        assert result == msgs

    @pytest.mark.asyncio
    async def test_loop_with_tool_call_then_final(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO_SAFE, sandbox_dir=".")
        responses = [
            {"message": {"tool_calls": [{"function": {"name": "file_exists", "arguments": {"path": "x"}}}]}},
            {"message": {"content": "final"}},
        ]
        idx = {"n": 0}

        async def fake_chat(msgs):
            r = responses[idx["n"]]
            idx["n"] += 1
            return r

        msgs = [{"role": "user", "content": "q"}]
        result = await m.process_tool_calls_loop(msgs, chat_func=fake_chat, max_iterations=3)
        assert any(m.get("role") == "tool" for m in result)
        assert result[-1]["message"]["content"] == "final"

    @pytest.mark.asyncio
    async def test_loop_skipped_dangerous_tool(self) -> None:
        m = _manager(mode=ToolExecutionMode.AUTO_SAFE, sandbox_dir=".")
        responses = [
            {"message": {"tool_calls": [{"function": {"name": "delete_file", "arguments": {"path": "x"}}}]}},
            {"message": {"content": "final"}},
        ]
        idx = {"n": 0}

        async def fake_chat(msgs):
            r = responses[idx["n"]]
            idx["n"] += 1
            return r

        msgs = [{"role": "user", "content": "q"}]
        result = await m.process_tool_calls_loop(msgs, chat_func=fake_chat, max_iterations=3)
        assert any("skipped" in str(m.get("content", "")) for m in result)
