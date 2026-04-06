"""Tests for tool execution manager."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from miru.tools import (
    ToolExecutionManager,
    ToolExecutionMode,
    ToolRegistry,
)
from miru.tools.execution import create_file_tools, create_system_tools


class TestToolExecutionMode:
    """Tests for ToolExecutionMode enum."""

    def test_mode_values(self) -> None:
        """Test execution mode values."""
        assert ToolExecutionMode.DISABLED.value == "disabled"
        assert ToolExecutionMode.MANUAL.value == "manual"
        assert ToolExecutionMode.AUTO.value == "auto"
        assert ToolExecutionMode.AUTO_SAFE.value == "auto_safe"

    def test_mode_comparison(self) -> None:
        """Test mode comparison."""
        assert ToolExecutionMode.AUTO != ToolExecutionMode.MANUAL
        assert ToolExecutionMode.DISABLED == ToolExecutionMode.DISABLED


class TestToolExecutionManager:
    """Tests for ToolExecutionManager class."""

    def test_init_disabled_mode(self, tmp_path: Path) -> None:
        """Test initializing with disabled mode."""
        manager = ToolExecutionManager(mode=ToolExecutionMode.DISABLED)

        assert manager.mode == ToolExecutionMode.DISABLED
        assert manager.is_tool_enabled() is False
        assert manager.get_tool_definitions() == []

    def test_init_with_sandbox(self, tmp_path: Path) -> None:
        """Test initializing with sandbox directory."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
            allow_write=True,
            allow_delete=False,
        )

        assert manager.sandbox_dir == tmp_path
        assert manager.has_tools()
        assert manager.is_tool_enabled()

    def test_init_without_sandbox(self) -> None:
        """Test initializing without sandbox."""
        manager = ToolExecutionManager(mode=ToolExecutionMode.AUTO)

        assert manager.sandbox_dir is None
        assert manager.has_tools()  # Still has system tools

    def test_get_tool_definitions_disabled(self) -> None:
        """Test getting definitions when disabled."""
        manager = ToolExecutionManager(mode=ToolExecutionMode.DISABLED)

        definitions = manager.get_tool_definitions()

        assert definitions == []

    def test_get_tool_definitions_auto(self, tmp_path: Path) -> None:
        """Test getting definitions in auto mode."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        definitions = manager.get_tool_definitions()

        assert len(definitions) > 0
        assert all("type" in d for d in definitions)
        assert all("function" in d for d in definitions)

    def test_should_execute_tool_disabled(self) -> None:
        """Test should_execute in disabled mode."""
        manager = ToolExecutionManager(mode=ToolExecutionMode.DISABLED)

        should_exec, reason = manager.should_execute_tool("test", {})

        assert should_exec is False
        assert "disabled" in reason.lower()

    def test_should_execute_tool_auto(self, tmp_path: Path) -> None:
        """Test should_execute in auto mode."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        should_exec, reason = manager.should_execute_tool("read_file", {"path": "test.txt"})

        assert should_exec is True
        assert reason is None

    def test_should_execute_tool_manual(self, tmp_path: Path) -> None:
        """Test should_execute in manual mode."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.MANUAL,
            sandbox_dir=tmp_path,
        )

        should_exec, reason = manager.should_execute_tool("read_file", {"path": "test.txt"})

        assert should_exec is False
        assert "manual" in reason.lower()

    def test_should_execute_tool_auto_safe(self, tmp_path: Path) -> None:
        """Test should_execute in auto_safe mode."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO_SAFE,
            sandbox_dir=tmp_path,
        )

        # Safe tool
        should_exec, reason = manager.should_execute_tool("read_file", {"path": "test.txt"})
        assert should_exec is True

        # Dangerous tool
        should_exec, reason = manager.should_execute_tool("delete_file", {"path": "test.txt"})
        assert should_exec is False
        assert "dangerous" in reason.lower()

    def test_execute_tool_success(self, tmp_path: Path) -> None:
        """Test executing a tool successfully."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        # Execute tool
        result, error = manager.execute_tool("read_file", {"path": "test.txt"})

        assert result == "Hello"
        assert error is None

    def test_execute_tool_error(self, tmp_path: Path) -> None:
        """Test executing a tool with error."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        # Execute non-existent file
        result, error = manager.execute_tool("read_file", {"path": "nonexistent.txt"})

        assert result is None
        assert error is not None

    def test_list_tools(self, tmp_path: Path) -> None:
        """Test listing available tools."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        tools = manager.list_tools()

        assert len(tools) > 0
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)

    def test_has_tools(self, tmp_path: Path) -> None:
        """Test checking if tools are available."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
        )

        assert manager.has_tools() is True

        # No sandbox, but still has system tools
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=None,
        )

        assert manager.has_tools() is True

    def test_allow_commands_flag(self) -> None:
        """Test allow_commands flag."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            allow_commands=True,
        )

        # Should have run_command available
        tool_names = [t["name"] for t in manager.list_tools()]
        assert "run_command" in tool_names

        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            allow_commands=False,
        )

        # run_command should still be registered but execution blocked
        # The flag affects execution, not registration
        assert manager.has_tools()

    def test_allow_env_flag(self) -> None:
        """Test allow_env flag."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            allow_env=True,
        )

        tools = manager.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "get_env" in tool_names

    def test_sandbox_write_permission(self, tmp_path: Path) -> None:
        """Test sandbox write permission."""
        # With write permission
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
            allow_write=True,
        )

        result, error = manager.execute_tool("write_file", {"path": "test.txt", "content": "test"})
        assert "success" in result.lower()
        assert error is None

        # Without write permission
        tmp_path2 = tmp_path / "sandbox2"
        tmp_path2.mkdir()
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path2,
            allow_write=False,
        )

        result, error = manager.execute_tool("write_file", {"path": "test.txt", "content": "test"})
        assert error is not None
        assert "disabled" in str(error).lower() or "denied" in str(error).lower()


class TestToolExtensionsSettings:
    """Tests for tools configuration via extensions."""

    def test_allowed_extensions(self, tmp_path: Path) -> None:
        """Test allowed extensions restriction."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
            allowed_extensions=[".txt", ".md"],
        )

        # Create files
        (tmp_path / "test.txt").write_text("text")
        (tmp_path / "test.py").write_text("code")

        # Read allowed extension
        result, error = manager.execute_tool("read_file", {"path": "test.txt"})
        assert result == "text"

        # Write allowed extension
        result, error = manager.execute_tool(
            "write_file", {"path": "test.md", "content": "markdown"}
        )
        assert "success" in result.lower()


class TestToolExecutionManagerIntegration:
    """Integration tests for ToolExecutionManager."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow from init to execution."""
        manager = ToolExecutionManager(
            mode=ToolExecutionMode.AUTO,
            sandbox_dir=tmp_path,
            allow_write=True,
        )

        # Check tools are available
        assert manager.is_tool_enabled()
        assert manager.has_tools()

        # Get definitions
        definitions = manager.get_tool_definitions()
        assert len(definitions) > 0

        # List tools
        tools = manager.list_tools()
        assert "read_file" in [t["name"] for t in tools]
        assert "write_file" in [t["name"] for t in tools]

        # Execute write
        result, error = manager.execute_tool(
            "write_file", {"path": "test.txt", "content": "Hello World"}
        )
        assert "success" in result.lower()
        assert error is None

        # Execute read
        result, error = manager.execute_tool("read_file", {"path": "test.txt"})
        assert result == "Hello World"

        # Execute list
        result, error = manager.execute_tool("list_files", {"directory": "."})
        assert isinstance(result, list)
        assert "test.txt" in result
