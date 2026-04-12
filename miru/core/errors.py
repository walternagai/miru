"""Custom exceptions for miru CLI.

Provides a consistent error handling strategy across the application.
"""

from typing import Any


class MiruError(Exception):
    """Base exception for all miru errors.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(self, message: str, suggestion: str | None = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.suggestion:
            return f"{self.message}\n\n{self.suggestion}"
        return self.message


class ModelNotFoundError(MiruError):
    """Raised when a requested model is not found.
    
    Attributes:
        model: The model name that was not found
        available_models: List of available models (optional)
    """
    
    def __init__(
        self, 
        model: str, 
        available_models: list[str] | None = None,
        suggestion: str | None = None
    ):
        self.model = model
        self.available_models = available_models or []
        
        from miru.core.i18n import t
        
        message = t("error.model_not_found", model=model)
        
        if not suggestion:
            if available_models:
                models_str = "\n  ".join(f"  • {m}" for m in available_models[:5])
                if len(available_models) > 5:
                    models_str += f"\n  {t('error.more_models', count=len(available_models) - 5)}"
                suggestion = f"{t('error.available_models')}\n{models_str}\n\n{t('suggestion.pull_model', model=model)}"
            else:
                suggestion = t("suggestion.pull_model", model=model)
        
        super().__init__(message, suggestion)


class ConnectionError(MiruError):
    """Raised when connection to Ollama server fails.
    
    Attributes:
        host: The host URL that failed
    """
    
    def __init__(self, host: str, original_error: Exception | None = None):
        self.host = host
        self.original_error = original_error
        
        from miru.core.i18n import t
        
        message = t("error.connection_failed", host=host)
        suggestion = t("suggestion.check_ollama")
        
        super().__init__(message, suggestion)


class ValidationError(MiruError):
    """Raised when input validation fails.
    
    Attributes:
        field: The field that failed validation
        value: The invalid value
    """
    
    def __init__(
        self, 
        message: str, 
        field: str | None = None,
        value: Any = None,
        suggestion: str | None = None
    ):
        self.field = field
        self.value = value
        
        super().__init__(message, suggestion)


class ToolExecutionError(MiruError):
    """Raised when tool execution fails.
    
    Attributes:
        tool_name: Name of the tool that failed
        arguments: Tool arguments
    """
    
    def __init__(
        self, 
        tool_name: str, 
        message: str,
        arguments: dict[str, Any] | None = None,
        suggestion: str | None = None
    ):
        self.tool_name = tool_name
        self.arguments = arguments or {}
        
        super().__init__(message, suggestion)


class ConfigError(MiruError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message, suggestion)


class FileProcessingError(MiruError):
    """Raised when file processing fails.
    
    Attributes:
        path: Path to the file that failed
        operation: The operation that failed (read, write, etc.)
    """
    
    def __init__(
        self, 
        path: str, 
        operation: str,
        original_error: Exception | None = None,
        suggestion: str | None = None
    ):
        self.path = path
        self.operation = operation
        self.original_error = original_error
        
        from miru.core.i18n import t
        
        message = f"Failed to {operation} file '{path}'"
        if original_error:
            message += f": {original_error}"
        
        super().__init__(message, suggestion)