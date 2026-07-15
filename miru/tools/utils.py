"""Utility functions for handling tool calls in responses."""

from typing import Any


def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract tool calls from a chat response.

    Args:
        response: Response dict from chat_with_tools

    Returns:
        List of tool call dicts, each with 'name' and 'arguments'

    Example:
        response = {
            "message": {
                "role": "assistant",
                "tool_calls": [{
                    "function": {
                        "name": "get_weather",
                        "arguments": {"city": "Tokyo"}
                    }
                }]
            }
        }
        calls = extract_tool_calls(response)
        # [{"name": "get_weather", "arguments": {"city": "Tokyo"}}]
    """
    message = response.get("message", {})
    tool_calls = message.get("tool_calls", [])

    extracted = []
    for call in tool_calls:
        if "function" in call:
            func = call["function"]
            extracted.append(
                {
                    "name": func.get("name", ""),
                    "arguments": func.get("arguments", {}),
                }
            )

    return extracted


def has_tool_calls(response: dict[str, Any]) -> bool:
    """
    Check if response contains tool calls.

    Args:
        response: Response dict from chat_with_tools

    Returns:
        True if response has tool_calls
    """
    message = response.get("message", {})
    return bool(message.get("tool_calls"))


def create_tool_result_message(
    tool_name: str,
    result: Any,
    error: Exception | None = None,
) -> dict[str, Any]:
    """
    Create a tool result message to send back to the model.

    Args:
        tool_name: Name of the tool that was executed
        result: Tool execution result
        error: Optional exception if tool failed

    Returns:
        Message dict with role 'tool'

    Example:
        msg = create_tool_result_message("get_weather", "15°C, sunny")
        # {"role": "tool", "content": "15°C, sunny", "tool_name": "get_weather"}
    """
    if error:
        content = f"Error: {error}"
    else:
        content = str(result)

    return {
        "role": "tool",
        "content": content,
        "tool_name": tool_name,
    }


def create_tool_call_message(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a tool call message for conversation history.

    Args:
        tool_name: Name of the tool
        arguments: Tool arguments

    Returns:
        Message dict with role 'assistant' and tool_calls

    Example:
        msg = create_tool_call_message("get_weather", {"city": "Tokyo"})
        # {
        #     "role": "assistant",
        #     "content": "",
        #     "tool_calls": [{
        #         "function": {
        #             "name": "get_weather",
        #             "arguments": {"city": "Tokyo"}
        #         }
        #     }]
        # }
    """
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": tool_name,
                    "arguments": arguments,
                }
            }
        ],
    }
