"""Base Tool class and related types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

P = Any  # Type alias for ParamSpec (simplified for mypy)
T = Any  # Type alias for TypeVar (simplified for mypy)


@dataclass
class Tool:
    """
    Represents a tool available for function calling.

    Tools are functions that can be executed by AI models through
    the Ollama tools/function calling API.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def to_ollama_format(self) -> dict[str, Any]:
        """
        Convert tool to Ollama API format.

        Returns:
            Dict in format expected by /api/chat endpoint
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def validate_arguments(self, arguments: dict[str, Any]) -> list[str]:
        """
        Validate tool arguments against parameters schema.

        Args:
            arguments: Arguments to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []
        params_schema = self.parameters

        if "required" in params_schema:
            for required_param in params_schema["required"]:
                if required_param not in arguments:
                    errors.append(f"Missing required parameter: {required_param}")

        if "properties" in params_schema:
            for param_name, param_value in arguments.items():
                if param_name not in params_schema["properties"]:
                    errors.append(f"Unknown parameter: {param_name}")
                    continue

                param_schema = params_schema["properties"][param_name]
                param_type = param_schema.get("type")

                if param_type and not self._validate_type(param_value, param_type):
                    errors.append(
                        f"Parameter '{param_name}' has wrong type: "
                        f"expected {param_type}, got {type(param_value).__name__}"
                    )

        return errors

    @staticmethod
    def _validate_type(value: Any, expected_type: str) -> bool:
        """
        Validate if value matches expected JSON schema type.

        Args:
            value: Value to validate
            expected_type: Expected JSON schema type

        Returns:
            True if type matches
        """
        type_mapping: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected_python_type = type_mapping.get(expected_type)
        if not expected_python_type:
            return True

        return isinstance(value, expected_python_type)


def create_tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to create a Tool from a function.

    Args:
        name: Tool name
        description: Tool description
        parameters: JSON schema of parameters

    Returns:
        Decorator function

    Example:
        @create_tool(
            name="read_file",
            description="Read file contents",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        )
        def read_file(path: str) -> str:
            return Path(path).read_text()
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._tool_metadata = Tool(  # type: ignore[attr-defined]
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
        )
        return func

    return decorator


def get_tool_from_function(func: Callable[..., Any]) -> Tool | None:
    """
    Extract Tool from a decorated function.

    Args:
        func: Function decorated with @create_tool

    Returns:
        Tool instance or None if not decorated
    """
    metadata = getattr(func, "_tool_metadata", None)
    if isinstance(metadata, Tool):
        return metadata
    return None
