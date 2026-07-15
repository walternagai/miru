"""System tools with security controls."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from miru.tools.base import Tool, create_tool


class SystemSecurityError(Exception):
    """Security-related error in system tool execution."""

    pass


class CommandWhitelist:
    """
    Whitelist of allowed shell commands.

    Provides fine-grained control over which commands
    can be executed by the AI model.
    """

    def __init__(self) -> None:
        """Initialize empty whitelist."""
        self._allowed_commands: dict[str, dict[str, Any]] = {}

    def allow(
        self,
        command: str,
        description: str = "",
        allowed_args: list[str] | None = None,
        dangerous: bool = False,
    ) -> None:
        """
        Add command to whitelist.

        Args:
            command: Command name or path (e.g., 'ls', '/usr/bin/git')
            description: Human-readable description
            allowed_args: List of allowed argument patterns (supports * and ?)
            dangerous: If True, requires explicit approval for each execution
        """
        self._allowed_commands[command] = {
            "description": description,
            "allowed_args": allowed_args,
            "dangerous": dangerous,
        }

    def deny(self, command: str) -> None:
        """Remove command from whitelist."""
        self._allowed_commands.pop(command, None)

    def is_allowed(self, command: str) -> bool:
        """Check if command is in whitelist."""
        # Check exact match
        if command in self._allowed_commands:
            return True

        # Check if command is in PATH and is allowed
        base_cmd = command.split()[0] if " " in command else command
        return bool(base_cmd in self._allowed_commands)

    def is_dangerous(self, command: str) -> bool:
        """Check if command is marked as dangerous."""
        base_cmd = command.split()[0] if " " in command else command
        info = self._allowed_commands.get(base_cmd, {})
        return info.get("dangerous", False)

    def get_allowed_args(self, command: str) -> list[str] | None:
        """Get allowed argument patterns for command."""
        base_cmd = command.split()[0] if " " in command else command
        info = self._allowed_commands.get(base_cmd, {})
        return info.get("allowed_args")

    def list_all(self) -> dict[str, dict[str, Any]]:
        """Get all allowed commands."""
        return self._allowed_commands.copy()


class EnvironmentWhitelist:
    """
    Whitelist of allowed environment variables.

    Controls which environment variables can be read by the AI.
    """

    def __init__(self) -> None:
        """Initialize empty whitelist."""
        self._allowed_vars: dict[str, str] = {}

    def allow(self, var: str, description: str = "") -> None:
        """
        Add environment variable to whitelist.

        Args:
            var: Variable name (e.g., 'HOME', 'PATH')
            description: Human-readable description
        """
        self._allowed_vars[var] = description

    def deny(self, var: str) -> None:
        """Remove variable from whitelist."""
        self._allowed_vars.pop(var, None)

    def is_allowed(self, var: str) -> bool:
        """Check if variable is in whitelist."""
        return var in self._allowed_vars

    def list_all(self) -> dict[str, str]:
        """Get all allowed variables."""
        return self._allowed_vars.copy()


def create_system_tools(
    cmd_whitelist: CommandWhitelist | None = None,
    env_whitelist: EnvironmentWhitelist | None = None,
    allow_commands: bool = False,
    allow_env: bool = True,
    working_dir: Path | str | None = None,
) -> list[Tool]:
    """
    Create system tools with security controls.

    Args:
        cmd_whitelist: Whitelist of allowed commands
        env_whitelist: Whitelist of allowed environment variables
        allow_commands: If False, run_command is disabled regardless of whitelist
        allow_env: If False, get_env is disabled regardless of whitelist
        working_dir: Working directory for commands (default: current directory)

    Returns:
        List of Tool instances for system operations
    """
    # Default whitelists if not provided
    if cmd_whitelist is None:
        cmd_whitelist = CommandWhitelist()
        # Add safe defaults
        cmd_whitelist.allow("ls", "List directory contents")
        cmd_whitelist.allow("pwd", "Print working directory")
        cmd_whitelist.allow("date", "Print current date/time")
        cmd_whitelist.allow("echo", "Print text to stdout")
        cmd_whitelist.allow("cat", "Concatenate and print files")
        cmd_whitelist.allow("head", "Print first lines of file")
        cmd_whitelist.allow("tail", "Print last lines of file")
        cmd_whitelist.allow("wc", "Print newline/word/byte counts")

    if env_whitelist is None:
        env_whitelist = EnvironmentWhitelist()
        # Add safe defaults
        env_whitelist.allow("HOME", "User home directory")
        env_whitelist.allow("USER", "Current username")
        env_whitelist.allow("PATH", "Executable search path")
        env_whitelist.allow("PWD", "Current working directory")
        env_whitelist.allow("LANG", "Locale settings")
        env_whitelist.allow("SHELL", "User's shell")
        env_whitelist.allow("EDITOR", "Default editor")
        env_whitelist.allow("TERM", "Terminal type")

    working_directory = Path(working_dir) if working_dir else Path.cwd()

    def run_command(cmd: str, timeout: int = 10) -> str:
        """
        Execute a shell command from the whitelist.

        Args:
            cmd: Command to execute (must be in whitelist)
            timeout: Timeout in seconds (default: 10)

        Returns:
            Command output (stdout)

        Raises:
            SystemSecurityError: If command not in whitelist or execution fails
        """
        if not allow_commands:
            raise SystemSecurityError("Command execution is disabled")

        if not cmd_whitelist.is_allowed(cmd):
            raise SystemSecurityError(
                f"Command not in whitelist: {cmd}. "
                f"Allowed commands: {', '.join(cmd_whitelist.list_all().keys())}"
            )

        if cmd_whitelist.is_dangerous(cmd):
            # In FASE 3, this would prompt user for approval
            raise SystemSecurityError(
                f"Command '{cmd}' is marked as dangerous and requires approval"
            )

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_directory,
                # Restrict environment
                env={k: os.environ[k] for k in os.environ if k in ["PATH", "HOME", "USER", "LANG"]},
            )

            if result.returncode != 0:
                return f"Error (exit code {result.returncode}): {result.stderr}"

            return result.stdout.strip() if result.stdout else "(no output)"

        except subprocess.TimeoutExpired:
            raise SystemSecurityError(f"Command timed out after {timeout} seconds")
        except Exception as e:
            raise SystemSecurityError(f"Command execution failed: {e}")

    def get_env(var: str) -> str:
        """
        Get value of an environment variable from the whitelist.

        Args:
            var: Environment variable name

        Returns:
            Variable value

        Raises:
            SystemSecurityError: If variable not in whitelist
        """
        if not allow_env:
            raise SystemSecurityError("Environment variable access is disabled")

        if not env_whitelist.is_allowed(var):
            raise SystemSecurityError(
                f"Environment variable not in whitelist: {var}. "
                f"Allowed variables: {', '.join(env_whitelist.list_all().keys())}"
            )

        value = os.environ.get(var, "")
        return f"{var}={value}" if value else f"{var} is not set"

    def get_current_dir() -> str:
        """
        Get current working directory.

        Returns:
            Absolute path of current directory
        """
        return str(working_directory)

    def list_allowed_commands() -> list[str]:
        """
        List all commands in the whitelist.

        Returns:
            List of allowed command names
        """
        return sorted(cmd_whitelist.list_all().keys())

    def list_allowed_env_vars() -> list[str]:
        """
        List all environment variables in the whitelist.

        Returns:
            List of allowed variable names
        """
        return sorted(env_whitelist.list_all().keys())

    # Create Tool objects
    tools = [
        create_tool(
            name="run_command",
            description="Execute a shell command from the whitelist",
            parameters={
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to execute (must be in whitelist)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 10)",
                    },
                },
                "required": ["cmd"],
            },
        )(run_command),
        create_tool(
            name="get_env",
            description="Get value of an environment variable",
            parameters={
                "type": "object",
                "properties": {
                    "var": {
                        "type": "string",
                        "description": "Environment variable name",
                    }
                },
                "required": ["var"],
            },
        )(get_env),
        create_tool(
            name="get_current_dir",
            description="Get current working directory",
            parameters={"type": "object", "properties": {}, "required": []},
        )(get_current_dir),
        create_tool(
            name="list_allowed_commands",
            description="List all commands in the whitelist",
            parameters={"type": "object", "properties": {}, "required": []},
        )(list_allowed_commands),
        create_tool(
            name="list_allowed_env_vars",
            description="List all environment variables in the whitelist",
            parameters={"type": "object", "properties": {}, "required": []},
        )(list_allowed_env_vars),
    ]

    # Extract Tool objects from decorated functions
    extracted: list[Tool] = []
    for func in tools:
        tool = get_tool_from_function(func)
        if tool is not None:
            extracted.append(tool)
    return extracted


__all__ = [
    "CommandWhitelist",
    "EnvironmentWhitelist",
    "SystemSecurityError",
    "create_system_tools",
]


# Import at end to avoid circular dependency
from miru.tools.base import get_tool_from_function
