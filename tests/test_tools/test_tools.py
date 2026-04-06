"""Tests for miru.tools module."""

import pytest

from miru.tools import (
    Tool,
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistry,
    ToolValidationError,
    create_tool,
    create_tool_call_message,
    create_tool_result_message,
    extract_tool_calls,
    get_tool_from_function,
    has_tool_calls,
)


class TestTool:
    """Tests for Tool class."""

    def test_tool_creation(self) -> None:
        """Test creating a Tool instance."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=lambda path: f"read {path}",
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert "path" in tool.parameters["properties"]

    def test_to_ollama_format(self) -> None:
        """Test converting Tool to Ollama API format."""
        tool = Tool(
            name="get_weather",
            description="Get weather for a city",
            parameters={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name"}},
                "required": ["city"],
            },
            handler=lambda city: f"Weather in {city}",
        )

        ollama_format = tool.to_ollama_format()

        assert ollama_format["type"] == "function"
        assert ollama_format["function"]["name"] == "get_weather"
        assert ollama_format["function"]["description"] == "Get weather for a city"
        assert "parameters" in ollama_format["function"]

    def test_validate_arguments_valid(self) -> None:
        """Test validating valid arguments."""
        tool = Tool(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=lambda value: value,
        )

        errors = tool.validate_arguments({"value": "hello"})
        assert errors == []

    def test_validate_arguments_missing_required(self) -> None:
        """Test validating arguments with missing required field."""
        tool = Tool(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=lambda value: value,
        )

        errors = tool.validate_arguments({})
        assert len(errors) == 1
        assert "Missing required parameter: value" in errors[0]

    def test_validate_arguments_wrong_type(self) -> None:
        """Test validating arguments with wrong type."""
        tool = Tool(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {"count": {"type": "integer"}},
                "required": ["count"],
            },
            handler=lambda count: count,
        )

        errors = tool.validate_arguments({"count": "not_an_int"})
        assert len(errors) == 1
        assert "wrong type" in errors[0]

    def test_validate_arguments_unknown_parameter(self) -> None:
        """Test validating arguments with unknown parameter."""
        tool = Tool(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": [],
            },
            handler=lambda value: value,
        )

        errors = tool.validate_arguments({"value": "ok", "unknown": "param"})
        assert len(errors) == 1
        assert "Unknown parameter" in errors[0]


class TestCreateTool:
    """Tests for create_tool decorator."""

    def test_create_tool_decorator(self) -> None:
        """Test creating tool from decorated function."""

        @create_tool(
            name="read_file",
            description="Read a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        def read_file(path: str) -> str:
            return f"content of {path}"

        assert hasattr(read_file, "_tool_metadata")
        tool = get_tool_from_function(read_file)
        assert tool is not None
        assert tool.name == "read_file"
        assert tool.description == "Read a file"

    def test_get_tool_from_non_decorated_function(self) -> None:
        """Test getting tool from non-decorated function."""

        def normal_function(x: int) -> int:
            return x * 2

        tool = get_tool_from_function(normal_function)
        assert tool is None


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test tool",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "ok",
        )

        registry.register(tool)

        assert "test" in registry
        assert len(registry) == 1

    def test_register_duplicate_tool(self) -> None:
        """Test registering duplicate tool raises error."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test tool",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "ok",
        )

        registry.register(tool)

        with pytest.raises(Exception) as exc_info:
            registry.register(tool)

        assert "already registered" in str(exc_info.value)

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test",
            parameters={},
            handler=lambda: "ok",
        )
        registry.register(tool)

        registry.unregister("test")

        assert "test" not in registry

    def test_unregister_nonexistent_tool(self) -> None:
        """Test unregistering non-existent tool raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError):
            registry.unregister("nonexistent")

    def test_get_tool(self) -> None:
        """Test getting a tool by name."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test",
            parameters={},
            handler=lambda: "ok",
        )
        registry.register(tool)

        retrieved = registry.get("test")

        assert retrieved.name == "test"

    def test_get_nonexistent_tool(self) -> None:
        """Test getting non-existent tool raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent")

    def test_list_tools(self) -> None:
        """Test listing all tools."""
        registry = ToolRegistry()
        tool1 = Tool(name="test1", description="Test 1", parameters={}, handler=lambda: 1)
        tool2 = Tool(name="test2", description="Test 2", parameters={}, handler=lambda: 2)

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()

        assert len(tools) == 2
        assert all(isinstance(t, Tool) for t in tools)

    def test_get_definitions(self) -> None:
        """Test getting tool definitions in Ollama format."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test tool",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
            handler=lambda x: x,
        )
        registry.register(tool)

        definitions = registry.get_definitions()

        assert len(definitions) == 1
        assert definitions[0]["type"] == "function"
        assert definitions[0]["function"]["name"] == "test"

    def test_execute_tool(self) -> None:
        """Test executing a tool."""
        registry = ToolRegistry()
        tool = Tool(
            name="add",
            description="Add two numbers",
            parameters={
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
            },
            handler=lambda a, b: a + b,
        )
        registry.register(tool)

        result = registry.execute("add", {"a": 5, "b": 3})

        assert result == 8

    def test_execute_tool_with_invalid_args(self) -> None:
        """Test executing tool with invalid arguments raises validation error."""
        registry = ToolRegistry()
        tool = Tool(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
            handler=lambda value: value * 2,
        )
        registry.register(tool)

        with pytest.raises(ToolValidationError):
            registry.execute("test", {})

    def test_execute_tool_with_exception(self) -> None:
        """Test executing tool that raises exception."""
        registry = ToolRegistry()
        tool = Tool(
            name="fail",
            description="Always fails",
            parameters={},
            handler=lambda: 1 / 0,
        )
        registry.register(tool)

        with pytest.raises(ToolExecutionError) as exc_info:
            registry.execute("fail", {})

        assert "execution failed" in str(exc_info.value)

    def test_clear_registry(self) -> None:
        """Test clearing all tools from registry."""
        registry = ToolRegistry()
        tool = Tool(name="test", description="Test", parameters={}, handler=lambda: "ok")
        registry.register(tool)

        registry.clear()

        assert len(registry) == 0

    def test_repr(self) -> None:
        """Test string representation."""
        registry = ToolRegistry()
        tool1 = Tool(name="tool1", description="Test", parameters={}, handler=lambda: 1)
        tool2 = Tool(name="tool2", description="Test", parameters={}, handler=lambda: 2)

        registry.register(tool1)
        registry.register(tool2)

        repr_str = repr(registry)

        assert "ToolRegistry" in repr_str
        assert "tool1" in repr_str
        assert "tool2" in repr_str


class TestToolUtils:
    """Tests for tool utility functions."""

    def test_extract_tool_calls(self) -> None:
        """Test extracting tool calls from response."""
        response = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": {"city": "Tokyo"},
                        }
                    }
                ],
            }
        }

        calls = extract_tool_calls(response)

        assert len(calls) == 1
        assert calls[0]["name"] == "get_weather"
        assert calls[0]["arguments"] == {"city": "Tokyo"}

    def test_extract_tool_calls_empty(self) -> None:
        """Test extracting tool calls from response without tool_calls."""
        response = {"message": {"role": "assistant", "content": "Hello"}}

        calls = extract_tool_calls(response)

        assert calls == []

    def test_has_tool_calls_true(self) -> None:
        """Test checking response has tool calls."""
        response = {
            "message": {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "test", "arguments": {}}}],
            }
        }

        assert has_tool_calls(response) is True

    def test_has_tool_calls_false(self) -> None:
        """Test checking response has no tool calls."""
        response = {"message": {"role": "assistant", "content": "Hello"}}

        assert has_tool_calls(response) is False

    def test_create_tool_result_message_success(self) -> None:
        """Test creating tool result message."""
        msg = create_tool_result_message("get_weather", "15°C, sunny")

        assert msg["role"] == "tool"
        assert msg["content"] == "15°C, sunny"
        assert msg["tool_name"] == "get_weather"

    def test_create_tool_result_message_error(self) -> None:
        """Test creating tool result message with error."""
        msg = create_tool_result_message("test", None, error=ValueError("test error"))

        assert msg["role"] == "tool"
        assert "Error: test error" in msg["content"]
        assert msg["tool_name"] == "test"

    def test_create_tool_call_message(self) -> None:
        """Test creating tool call message."""
        msg = create_tool_call_message("get_weather", {"city": "Tokyo"})

        assert msg["role"] == "assistant"
        assert msg["content"] == ""
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["function"]["name"] == "get_weather"
        assert msg["tool_calls"][0]["function"]["arguments"] == {"city": "Tokyo"}
