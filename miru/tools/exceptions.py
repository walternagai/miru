"""Exceptions for tools module."""


class ToolNotFoundError(Exception):
    """Requested tool was not found in registry."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Tool '{name}' not found")


class ToolExecutionError(Exception):
    """Error during tool execution."""

    def __init__(self, name: str, message: str) -> None:
        self.name = name
        self.message = message
        super().__init__(f"Tool '{name}' execution failed: {message}")


class ToolValidationError(Exception):
    """Tool arguments validation failed."""

    def __init__(self, name: str, errors: list[str]) -> None:
        self.name = name
        self.errors = errors
        error_msg = "; ".join(errors)
        super().__init__(f"Tool '{name}' validation failed: {error_msg}")


class ToolRegistryError(Exception):
    """Base exception for tool registry errors."""

    pass
