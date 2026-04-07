"""Tests for core.errors module."""

import pytest
from miru.core.errors import (
    MiruError,
    ModelNotFoundError,
    ConnectionError,
    ValidationError,
    ToolExecutionError,
    ConfigError,
    FileProcessingError,
)
from miru.core.i18n import set_language


class TestMiruError:
    """Test base MiruError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = MiruError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.suggestion is None

    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        error = MiruError("Test error", suggestion="Try this")
        assert "Test error" in str(error)
        assert "Try this" in str(error)

    def test_error_str_without_suggestion(self):
        """Test string representation without suggestion."""
        error = MiruError("Test error")
        assert str(error) == "Test error"


class TestModelNotFoundError:
    """Test ModelNotFoundError."""

    def test_basic_not_found(self):
        """Test basic model not found error."""
        set_language("en_US")
        error = ModelNotFoundError("gemma3")
        assert "gemma3" in error.message
        assert error.model == "gemma3"
        assert error.suggestion is not None

    def test_not_found_with_available_models(self):
        """Test error with available models list."""
        set_language("en_US")
        error = ModelNotFoundError("gemma3", available_models=["llama3", "qwen2"])
        assert "gemma3" in error.message
        assert "llama3" in error.suggestion
        assert "qwen2" in error.suggestion

    def test_not_found_pt_br(self):
        """Test error in Portuguese."""
        set_language("pt_BR")
        error = ModelNotFoundError("gemma3")
        assert "não encontrado" in error.message.lower()

    def test_not_found_es_es(self):
        """Test error in Spanish."""
        set_language("es_ES")
        error = ModelNotFoundError("gemma3")
        assert "no encontrado" in error.message.lower()


class TestConnectionError:
    """Test ConnectionError."""

    def test_connection_error(self):
        """Test basic connection error."""
        set_language("en_US")
        error = ConnectionError("http://localhost:11434")
        assert "localhost" in error.message
        assert error.host == "http://localhost:11434"
        assert error.suggestion is not None

    def test_connection_error_pt_br(self):
        """Test connection error in Portuguese."""
        set_language("pt_BR")
        error = ConnectionError("http://localhost:11434")
        assert "conectar" in error.message.lower()

    def test_connection_error_with_original(self):
        """Test connection error with original exception."""
        original = Exception("Network unreachable")
        error = ConnectionError("http://localhost:11434", original)
        assert error.original_error == original


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid value")
        assert error.message == "Invalid value"
        assert error.field is None
        assert error.value is None

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        error = ValidationError("Invalid value", field="temperature")
        assert error.field == "temperature"

    def test_validation_error_with_value(self):
        """Test validation error with value."""
        error = ValidationError("Invalid value", value=-1)
        assert error.value == -1


class TestToolExecutionError:
    """Test ToolExecutionError."""

    def test_tool_error(self):
        """Test basic tool execution error."""
        error = ToolExecutionError("read_file", "Permission denied")
        assert error.tool_name == "read_file"
        assert "Permission denied" in error.message
        assert error.arguments == {}

    def test_tool_error_with_arguments(self):
        """Test tool error with arguments."""
        error = ToolExecutionError(
            "write_file",
            "Write failed",
            arguments={"path": "/etc/passwd", "content": "test"}
        )
        assert error.arguments["path"] == "/etc/passwd"


class TestConfigError:
    """Test ConfigError."""

    def test_config_error(self):
        """Test basic config error."""
        error = ConfigError("Invalid configuration")
        assert error.message == "Invalid configuration"

    def test_config_error_with_suggestion(self):
        """Test config error with suggestion."""
        error = ConfigError("Invalid config", suggestion="Run miru setup")
        assert "Run miru setup" in str(error)


class TestFileProcessingError:
    """Test FileProcessingError."""

    def test_file_error(self):
        """Test basic file processing error."""
        error = FileProcessingError("/path/to/file", "read")
        assert error.path == "/path/to/file"
        assert error.operation == "read"
        assert "read" in error.message.lower()
        assert "/path/to/file" in error.message

    def test_file_error_with_original(self):
        """Test file error with original exception."""
        original = PermissionError("Access denied")
        error = FileProcessingError("/path/to/file", "write", original)
        assert error.original_error == original
        assert "Access denied" in error.message

    def test_file_read_error(self):
        """Test read operation error."""
        error = FileProcessingError("/data/file.txt", "read")
        assert "read" in error.message.lower()

    def test_file_write_error(self):
        """Test write operation error."""
        error = FileProcessingError("/data/file.txt", "write")
        assert "write" in error.message.lower()