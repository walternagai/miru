"""Tests for system tools with security controls."""

import os
from pathlib import Path

import pytest

from miru.tools import (
    CommandWhitelist,
    EnvironmentWhitelist,
    SystemSecurityError,
    ToolRegistry,
    create_system_tools,
)


class TestCommandWhitelist:
    """Tests for CommandWhitelist class."""

    def test_empty_whitelist(self) -> None:
        """Test creating empty whitelist."""
        whitelist = CommandWhitelist()

        assert whitelist.is_allowed("ls") is False
        assert len(whitelist.list_all()) == 0

    def test_add_command(self) -> None:
        """Test adding command to whitelist."""
        whitelist = CommandWhitelist()
        whitelist.allow("ls", "List directory contents")

        assert whitelist.is_allowed("ls") is True
        assert "ls" in whitelist.list_all()

    def test_remove_command(self) -> None:
        """Test removing command from whitelist."""
        whitelist = CommandWhitelist()
        whitelist.allow("ls")
        whitelist.deny("ls")

        assert whitelist.is_allowed("ls") is False

    def test_command_with_args(self) -> None:
        """Test command with allowed args."""
        whitelist = CommandWhitelist()
        whitelist.allow("git", "Git version control", allowed_args=["status", "log"])

        assert whitelist.is_allowed("git") is True
        assert whitelist.get_allowed_args("git") == ["status", "log"]

    def test_dangerous_command(self) -> None:
        """Test marking command as dangerous."""
        whitelist = CommandWhitelist()
        whitelist.allow("rm", "Remove files", dangerous=True)

        assert whitelist.is_allowed("rm") is True
        assert whitelist.is_dangerous("rm") is True

    def test_non_dangerous_command(self) -> None:
        """Test normal command is not dangerous."""
        whitelist = CommandWhitelist()
        whitelist.allow("ls")

        assert whitelist.is_dangerous("ls") is False

    def test_list_all(self) -> None:
        """Test listing all allowed commands."""
        whitelist = CommandWhitelist()
        whitelist.allow("ls", "List files")
        whitelist.allow("pwd", "Print working directory")

        all_commands = whitelist.list_all()

        assert len(all_commands) == 2
        assert all_commands["ls"]["description"] == "List files"
        assert all_commands["pwd"]["description"] == "Print working directory"


class TestEnvironmentWhitelist:
    """Tests for EnvironmentWhitelist class."""

    def test_empty_whitelist(self) -> None:
        """Test creating empty whitelist."""
        whitelist = EnvironmentWhitelist()

        assert whitelist.is_allowed("HOME") is False
        assert len(whitelist.list_all()) == 0

    def test_add_variable(self) -> None:
        """Test adding variable to whitelist."""
        whitelist = EnvironmentWhitelist()
        whitelist.allow("HOME", "User home directory")

        assert whitelist.is_allowed("HOME") is True
        assert "HOME" in whitelist.list_all()

    def test_remove_variable(self) -> None:
        """Test removing variable from whitelist."""
        whitelist = EnvironmentWhitelist()
        whitelist.allow("HOME")
        whitelist.deny("HOME")

        assert whitelist.is_allowed("HOME") is False

    def test_list_all(self) -> None:
        """Test listing all allowed variables."""
        whitelist = EnvironmentWhitelist()
        whitelist.allow("HOME", "Home directory")
        whitelist.allow("PATH", "Executable path")

        all_vars = whitelist.list_all()

        assert len(all_vars) == 2
        assert all_vars["HOME"] == "Home directory"


class TestSystemTools:
    """Tests for system tools."""

    def test_get_current_dir(self) -> None:
        """Test getting current directory."""
        tools = create_system_tools()
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("get_current_dir", {})

        assert isinstance(result, str)
        assert Path(result).is_absolute()

    def test_get_current_dir_custom_workdir(self, tmp_path: Path) -> None:
        """Test getting current directory with custom working dir."""
        tools = create_system_tools(working_dir=tmp_path)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("get_current_dir", {})

        assert result == str(tmp_path)

    def test_get_env_allowed(self) -> None:
        """Test getting allowed environment variable."""
        os.environ["TEST_VAR"] = "test_value"

        env_whitelist = EnvironmentWhitelist()
        env_whitelist.allow("TEST_VAR")

        tools = create_system_tools(env_whitelist=env_whitelist)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("get_env", {"var": "TEST_VAR"})

        assert "TEST_VAR=test_value" in result

        # Cleanup
        del os.environ["TEST_VAR"]

    def test_get_env_not_in_whitelist(self) -> None:
        """Test getting env var not in whitelist."""
        os.environ["SECRET_VAR"] = "secret"

        env_whitelist = EnvironmentWhitelist()
        env_whitelist.allow("HOME")

        tools = create_system_tools(env_whitelist=env_whitelist)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="not in whitelist"):
            registry.execute("get_env", {"var": "SECRET_VAR"})

        # Cleanup
        del os.environ["SECRET_VAR"]

    def test_get_env_not_set(self) -> None:
        """Test getting env var that is not set."""
        env_whitelist = EnvironmentWhitelist()
        env_whitelist.allow("NONEXISTENT_VAR")

        tools = create_system_tools(env_whitelist=env_whitelist)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("get_env", {"var": "NONEXISTENT_VAR"})

        assert "not set" in result

    def test_get_env_disabled(self) -> None:
        """Test getting env when disabled."""
        tools = create_system_tools(allow_env=False)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="disabled"):
            registry.execute("get_env", {"var": "HOME"})

    def test_run_command_allowed(self) -> None:
        """Test running allowed command."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("echo")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("run_command", {"cmd": "echo hello"})

        assert "hello" in result

    def test_run_command_not_in_whitelist(self) -> None:
        """Test running command not in whitelist."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("ls")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="not in whitelist"):
            registry.execute("run_command", {"cmd": "rm -rf /"})

    def test_run_command_dangerous(self) -> None:
        """Test running command marked as dangerous."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("rm", dangerous=True)

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="dangerous"):
            registry.execute("run_command", {"cmd": "rm test.txt"})

    def test_run_command_disabled(self) -> None:
        """Test running command when disabled."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("ls")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=False)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="disabled"):
            registry.execute("run_command", {"cmd": "ls"})

    def test_run_command_timeout(self) -> None:
        """Test command timeout."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("sleep")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError, match="timed out"):
            registry.execute("run_command", {"cmd": "sleep 10", "timeout": 1})

    def test_run_command_custom_timeout(self) -> None:
        """Test command with custom timeout."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("echo")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("run_command", {"cmd": "echo test", "timeout": 5})

        assert "test" in result

    def test_run_command_error_output(self) -> None:
        """Test command that exits with error."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("ls")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("run_command", {"cmd": "ls /nonexistent_directory_12345"})

        assert "Error" in result or "error" in result.lower()

    def test_run_command_empty_output(self) -> None:
        """Test command with no output."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("true")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist, allow_commands=True)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("run_command", {"cmd": "true"})

        assert "no output" in result or result == ""

    def test_list_allowed_commands(self) -> None:
        """Test listing allowed commands."""
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("ls")
        cmd_whitelist.allow("pwd")
        cmd_whitelist.allow("echo")

        tools = create_system_tools(cmd_whitelist=cmd_whitelist)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("list_allowed_commands", {})

        assert isinstance(result, list)
        assert "ls" in result
        assert "pwd" in result
        assert "echo" in result

    def test_list_allowed_env_vars(self) -> None:
        """Test listing allowed environment variables."""
        env_whitelist = EnvironmentWhitelist()
        env_whitelist.allow("HOME")
        env_whitelist.allow("PATH")

        tools = create_system_tools(env_whitelist=env_whitelist)
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        result = registry.execute("list_allowed_env_vars", {})

        assert isinstance(result, list)
        assert "HOME" in result
        assert "PATH" in result

    def test_default_whitelist(self) -> None:
        """Test default whitelist has safe commands."""
        tools = create_system_tools()
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        # Should have safe commands by default
        allowed = registry.execute("list_allowed_commands", {})

        assert "ls" in allowed
        assert "pwd" in allowed
        assert "date" in allowed

        # Should not have dangerous commands
        assert "rm" not in allowed
        assert "sudo" not in allowed

    def test_default_env_whitelist(self) -> None:
        """Test default environment whitelist."""
        tools = create_system_tools()
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        allowed = registry.execute("list_allowed_env_vars", {})

        # Should have safe env vars by default
        assert "HOME" in allowed
        assert "USER" in allowed
        assert "PATH" in allowed


class TestSystemToolDefinitions:
    """Tests for system tool definitions."""

    def test_all_tools_have_correct_names(self) -> None:
        """Test all tools have expected names."""
        tools = create_system_tools()

        expected_names = {
            "run_command",
            "get_env",
            "get_current_dir",
            "list_allowed_commands",
            "list_allowed_env_vars",
        }

        actual_names = {tool.name for tool in tools}

        assert actual_names == expected_names

    def test_run_command_parameters(self) -> None:
        """Test run_command has correct parameters."""
        tools = create_system_tools()
        run_tool = next(t for t in tools if t.name == "run_command")

        assert "cmd" in run_tool.parameters["properties"]
        assert "timeout" in run_tool.parameters["properties"]
        assert run_tool.parameters["required"] == ["cmd"]

    def test_get_env_parameters(self) -> None:
        """Test get_env has correct parameters."""
        tools = create_system_tools()
        env_tool = next(t for t in tools if t.name == "get_env")

        assert "var" in env_tool.parameters["properties"]
        assert env_tool.parameters["required"] == ["var"]

    def test_tools_to_ollama_format(self) -> None:
        """Test converting tools to Ollama format."""
        tools = create_system_tools()

        for tool in tools:
            ollama_format = tool.to_ollama_format()

            assert ollama_format["type"] == "function"
            assert "function" in ollama_format
            assert ollama_format["function"]["name"] == tool.name
            assert "description" in ollama_format["function"]
            assert "parameters" in ollama_format["function"]


class TestSystemToolsIntegration:
    """Integration tests for system tools with registry."""

    def test_register_and_use_tools(self) -> None:
        """Test registering and using system tools."""
        # Create custom whitelist
        cmd_whitelist = CommandWhitelist()
        cmd_whitelist.allow("echo")
        cmd_whitelist.allow("pwd")

        env_whitelist = EnvironmentWhitelist()
        env_whitelist.allow("HOME")

        # Create and register tools
        tools = create_system_tools(
            cmd_whitelist=cmd_whitelist,
            env_whitelist=env_whitelist,
            allow_commands=True,
        )

        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)

        # Use tools
        pwd_result = registry.execute("get_current_dir", {})
        assert Path(pwd_result).is_absolute()

        echo_result = registry.execute("run_command", {"cmd": "echo test"})
        assert "test" in echo_result

        home_result = registry.execute("get_env", {"var": "HOME"})
        assert "HOME=" in home_result

    def test_tools_with_file_and_system(self, tmp_path: Path) -> None:
        """Test using both file and system tools together."""
        from miru.tools import FileSandbox, create_file_tools

        # Create file tools
        file_sandbox = FileSandbox(tmp_path)
        file_tools = create_file_tools(file_sandbox)

        # Create system tools
        system_tools = create_system_tools(allow_commands=False)

        # Register all in same registry
        registry = ToolRegistry()
        for tool in file_tools:
            registry.register(tool)
        for tool in system_tools:
            registry.register(tool)

        from miru.tools.exceptions import ToolExecutionError

        # Use file tools
        registry.execute("write_file", {"path": "test.txt", "content": "Hello"})
        content = registry.execute("read_file", {"path": "test.txt"})
        assert content == "Hello"

        # Use system tools (commands disabled)
        registry.execute("get_current_dir", {})
        with pytest.raises(ToolExecutionError):
            registry.execute("run_command", {"cmd": "ls"})
