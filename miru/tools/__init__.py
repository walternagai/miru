"""Tools/function calling support for miru.

This module provides infrastructure for AI models to execute tools
through Ollama's function calling API.

Example:
    from miru.tools import Tool, ToolRegistry, create_tool

    # Create a tool
    @create_tool(
        name="read_file",
        description="Read contents of a text file",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["path"]
        }
    )
    def read_file(path: str) -> str:
        return open(path).read()

    # Register and execute
    registry = ToolRegistry()
    tool = get_tool_from_function(read_file)
    registry.register(tool)

    # Get definitions for API
    definitions = registry.get_definitions()

    # Execute tool
    result = registry.execute("read_file", {"path": "/etc/hosts"})
"""

from miru.tools.base import Tool, create_tool, get_tool_from_function
from miru.tools.exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistryError,
    ToolValidationError,
)
from miru.tools.registry import ToolRegistry
from miru.tools.utils import (
    create_tool_call_message,
    create_tool_result_message,
    extract_tool_calls,
    has_tool_calls,
)

# Import from submodules
from miru.tools.files import FileSandbox, SecurityError, create_file_tools
from miru.tools.system import (
    CommandWhitelist,
    EnvironmentWhitelist,
    SystemSecurityError,
    create_system_tools,
)

# Import Tavily tools
from miru.tools.tavily import (
    TavilyClient,
    TavilyError,
    create_tavily_tools,
)

# Import execution and approval
from miru.tools.execution import ToolExecutionManager, ToolExecutionMode
from miru.tools.approval import ToolApprovalFlow, ToolApprovalManager

__all__ = [
    # Base
    "Tool",
    "ToolRegistry",
    "create_tool",
    "get_tool_from_function",
    # Exceptions
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolValidationError",
    "ToolRegistryError",
    "SecurityError",
    "SystemSecurityError",
    "TavilyError",
    # Utilities
    "extract_tool_calls",
    "has_tool_calls",
    "create_tool_result_message",
    "create_tool_call_message",
    # File tools
    "FileSandbox",
    "create_file_tools",
    # System tools
    "CommandWhitelist",
    "EnvironmentWhitelist",
    "create_system_tools",
    # Tavily tools
    "TavilyClient",
    "create_tavily_tools",
    # Execution
    "ToolExecutionManager",
    "ToolExecutionMode",
    # Approval
    "ToolApprovalFlow",
    "ToolApprovalManager",
]
