"""Tool execution manager for chat integration."""

from __future__ import annotations

import warnings
from enum import Enum
from pathlib import Path
from typing import Any

from miru.tools import (
    CommandWhitelist,
    EnvironmentWhitelist,
    FileSandbox,
    ToolRegistry,
    create_file_tools,
    create_system_tools,
)
from miru.tools.tavily import TavilyError, create_tavily_tools
from miru.tools.utils import create_tool_result_message, extract_tool_calls, has_tool_calls


class ToolExecutionMode(Enum):
    """Tool execution mode."""

    DISABLED = "disabled"  # Tools not available
    MANUAL = "manual"  # Ask before each tool execution
    AUTO = "auto"  # Execute automatically
    AUTO_SAFE = "auto_safe"  # Execute safe tools automatically, ask for dangerous ones


class ToolExecutionManager:
    """
    Manages tool execution during chat sessions.

    Handles:
    - Tool registration and discovery
    - Execution mode control
    - Sandbox configuration
    - Approval flow for dangerous tools
    - Tool call loop management
    """

    def __init__(
        self,
        mode: ToolExecutionMode = ToolExecutionMode.DISABLED,
        sandbox_dir: Path | str | None = None,
        allow_write: bool = True,
        allow_delete: bool = False,
        allowed_extensions: list[str] | None = None,
        allow_commands: bool = False,
        allow_env: bool = True,
        enable_tavily: bool = False,
        tavily_api_key: str | None = None,
    ) -> None:
        """
        Initialize tool execution manager.

        Args:
            mode: Execution mode
            sandbox_dir: Directory for file sandbox (None = disable file tools)
            allow_write: Allow write operations in sandbox
            allow_delete: Allow delete operations in sandbox
            allowed_extensions: List of allowed file extensions
            allow_commands: Allow command execution
            allow_env: Allow environment variable access
            enable_tavily: Enable Tavily web search tools
            tavily_api_key: Tavily API key (uses config/env if None)
        """
        self.mode = mode
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else None
        self.allow_write = allow_write
        self.allow_delete = allow_delete
        self.allowed_extensions = allowed_extensions
        self.allow_commands = allow_commands
        self.allow_env = allow_env
        self.enable_tavily = enable_tavily
        self.tavily_api_key = tavily_api_key

        self.registry = ToolRegistry()
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize and register all available tools."""
        # File tools
        if self.sandbox_dir:
            sandbox = FileSandbox(
                root=self.sandbox_dir,
                allow_write=self.allow_write,
                allow_delete=self.allow_delete,
                allowed_extensions=self.allowed_extensions,
            )
            for tool in create_file_tools(sandbox):
                self.registry.register(tool)

        # System tools
        for tool in create_system_tools(
            allow_commands=self.allow_commands,
            allow_env=self.allow_env,
            working_dir=self.sandbox_dir or Path.cwd(),
        ):
            self.registry.register(tool)

        # Tavily web search tools
        if self.enable_tavily:
            try:
                tavily_tools = create_tavily_tools(self.tavily_api_key)
                for tool in tavily_tools:
                    self.registry.register(tool)
            except TavilyError as e:
                warnings.warn(f"Failed to initialize Tavily tools: {e}", UserWarning)

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get tool definitions for Ollama API.

        Returns:
            List of tool definitions (empty if mode is DISABLED)
        """
        if self.mode == ToolExecutionMode.DISABLED:
            return []

        return self.registry.get_definitions()

    def should_execute_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Determine if tool should be executed based on mode and safety.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tuple of (should_execute, reason_if_skipped)
        """
        if self.mode == ToolExecutionMode.DISABLED:
            return False, "Tools are disabled"

        tool = self.registry.get(tool_name)

        # Check if tool exists
        if not tool:
            return False, f"Tool '{tool_name}' not found"

        # Check mode
        if self.mode == ToolExecutionMode.AUTO:
            return True, None

        if self.mode == ToolExecutionMode.MANUAL:
            return False, "Manual approval required"

        if self.mode == ToolExecutionMode.AUTO_SAFE:
            # Auto-execute safe tools, require approval for dangerous ones
            dangerous_tools = {"delete_file"}
            if tool_name in dangerous_tools:
                return False, "Dangerous tool requires approval"
            return True, None

        return False, "Unknown execution mode"

    def execute_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[Any, Exception | None]:
        """
        Execute a tool and return result.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tuple of (result, error_if_any)
        """
        try:
            result = self.registry.execute(tool_name, arguments)
            return result, None
        except Exception as e:
            return None, e

    def list_tools(self) -> list[dict[str, str]]:
        """
        List all available tools with descriptions.

        Returns:
            List of dicts with name and description
        """
        tools = []
        for tool in self.registry.list_tools():
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                }
            )
        return tools

    def is_tool_enabled(self) -> bool:
        """Check if tools are enabled."""
        return self.mode != ToolExecutionMode.DISABLED

    def has_tools(self) -> bool:
        """Check if any tools are registered."""
        return len(self.registry) > 0

    async def process_tool_calls_loop(
        self,
        messages: list[dict[str, Any]],
        chat_func: Any,  # Callable to get next response
        max_iterations: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Process tool calls in a loop until final response.

        Args:
            messages: Conversation history
            chat_func: Async function to get next model response
            max_iterations: Maximum tool call iterations

        Returns:
            Updated messages list
        """
        if self.mode == ToolExecutionMode.DISABLED:
            return messages

        for _ in range(max_iterations):
            # Get next response
            response = await chat_func(messages)

            # Check for tool calls
            tool_calls = extract_tool_calls(response)
            if not tool_calls:
                # No more tool calls, add final response
                messages.append(response)
                break

            # Process each tool call
            for call in tool_calls:
                tool_name = call.get("name", "")
                arguments = call.get("arguments", {})

                should_exec, reason = self.should_execute_tool(tool_name, arguments)

                if should_exec:
                    result, error = self.execute_tool(tool_name, arguments)
                    tool_message = create_tool_result_message(tool_name, result, error)
                    messages.append(tool_message)
                else:
                    # Add skip message
                    messages.append(
                        {
                            "role": "tool",
                            "content": f"Tool execution skipped: {reason}",
                            "tool_name": tool_name,
                        }
                    )

        return messages


__all__ = [
    "ToolExecutionMode",
    "ToolExecutionManager",
]
