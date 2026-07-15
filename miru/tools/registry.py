"""Tool registry for managing available tools."""

from __future__ import annotations

from typing import Any

from miru.tools.base import Tool
from miru.tools.exceptions import ToolNotFoundError, ToolRegistryError, ToolValidationError


class ToolRegistry:
    """
    Manages available tools for function calling.

    The registry stores tool definitions and handlers, provides validation,
    and executes tools when called by AI models.
    """

    def __init__(self) -> None:
        """Initialize empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ToolRegistryError: If tool with same name already exists
        """
        if tool.name in self._tools:
            raise ToolRegistryError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """
        Remove a tool from the registry.

        Args:
            name: Tool name to remove

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        del self._tools[name]

    def get(self, name: str) -> Tool:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def list_tools(self) -> list[Tool]:
        """
        List all registered tools.

        Returns:
            List of Tool instances
        """
        return list(self._tools.values())

    def get_definitions(self) -> list[dict[str, Any]]:
        """
        Get tool definitions in Ollama API format.

        Returns:
            List of tool definitions to send to API
        """
        return [tool.to_ollama_format() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Execute a tool with given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ToolNotFoundError: If tool not found
            ToolValidationError: If arguments invalid
            ToolExecutionError: If execution fails
        """
        from miru.tools.exceptions import ToolExecutionError

        tool = self.get(name)

        validation_errors = tool.validate_arguments(arguments)
        if validation_errors:
            raise ToolValidationError(name, validation_errors)

        try:
            result = tool.handler(**arguments)
            return result
        except Exception as e:
            raise ToolExecutionError(name, str(e)) from e

    def clear(self) -> None:
        """Remove all tools from registry."""
        self._tools.clear()

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation."""
        tool_names = list(self._tools.keys())
        return f"ToolRegistry(tools={tool_names})"
