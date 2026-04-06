"""Tool integration helpers for chat/run commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from miru.config_manager import get_config_value
from miru.ollama.client import OllamaClient
from miru.output.renderer import render_markdown
from miru.tools import ToolExecutionManager, ToolExecutionMode
from miru.tools.utils import (
    create_tool_result_message,
    create_tool_call_message,
    extract_tool_calls,
    has_tool_calls,
)


def create_tool_manager(
    enable_tools: bool = False,
    enable_tavily: bool = False,
    sandbox_dir: str | None = None,
    tool_mode: str = "auto_safe",
) -> ToolExecutionManager | None:
    """Create tool execution manager if tools are enabled.

    Args:
        enable_tools: Enable all tools
        enable_tavily: Enable Tavily web search specifically
        sandbox_dir: Sandbox directory for file operations
        tool_mode: Execution mode (disabled/manual/auto/auto_safe)

    Returns:
        ToolExecutionManager or None if tools not enabled
    """
    if not enable_tools and not enable_tavily:
        return None

    mode_map = {
        "disabled": ToolExecutionMode.DISABLED,
        "manual": ToolExecutionMode.MANUAL,
        "auto": ToolExecutionMode.AUTO,
        "auto_safe": ToolExecutionMode.AUTO_SAFE,
    }
    mode = mode_map.get(tool_mode, ToolExecutionMode.AUTO_SAFE)

    sandbox = Path(sandbox_dir) if sandbox_dir else Path.cwd() / ".miru_sandbox"

    tavily_api_key = get_config_value("tavily_api_key")
    if tavily_api_key is not None:
        tavily_api_key = str(tavily_api_key)

    manager = ToolExecutionManager(
        mode=mode,
        sandbox_dir=sandbox,
        enable_tavily=enable_tavily or enable_tools,
        tavily_api_key=tavily_api_key if enable_tavily or enable_tools else None,
    )

    return manager


async def process_tool_calls(
    client: OllamaClient,
    model: str,
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    tool_manager: ToolExecutionManager,
    quiet: bool = False,
) -> list[dict[str, Any]]:
    """Process tool calls and return updated messages.

    Args:
        client: Ollama client
        model: Model name
        messages: Current message history
        tool_calls: List of tool calls to process
        tool_manager: Tool execution manager
        quiet: Suppress output

    Returns:
        Updated messages list with tool results
    """
    for call in tool_calls:
        tool_name = call.get("name", "")
        arguments = call.get("arguments", {})

        if not quiet:
            print(f"\n[Tool] Executando: {tool_name}({arguments})\n")

        result, error = tool_manager.execute_tool(tool_name, arguments)

        if error and not quiet:
            print(f"[Tool] Erro: {error}\n")

        tool_result_msg = create_tool_result_message(tool_name, result, error)
        messages.append(tool_result_msg)

    return messages


async def execute_tool_loop(
    client: OllamaClient,
    model: str,
    messages: list[dict[str, Any]],
    tool_manager: ToolExecutionManager,
    options: dict[str, Any],
    quiet: bool = False,
    max_iterations: int = 10,
) -> str:
    """Execute tool loop until model returns final response.

    Args:
        client: Ollama client
        model: Model name
        messages: Conversation history
        tool_manager: Tool execution manager
        options: Model options
        quiet: Suppress output
        max_iterations: Maximum tool iterations

    Returns:
        Final model response text
    """
    tools = tool_manager.get_tool_definitions()

    for iteration in range(max_iterations):
        if not quiet:
            print(f"\n[dim]⟳ Iteração {iteration + 1}/{max_iterations}[/]")

        chunks = client.chat_with_tools(model, messages, tools=tools, options=options, stream=True)

        response_parts = []
        current_tool_calls = []

        async for chunk in chunks:
            if has_tool_calls(chunk):
                calls = extract_tool_calls(chunk)
                current_tool_calls.extend(calls)
            else:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    response_parts.append(content)
                    if not quiet:
                        print(content, end="", flush=True)

        if current_tool_calls:
            # Show newline after partial response if any
            if not quiet and response_parts:
                print()

            for call in current_tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": call["name"],
                                    "arguments": call["arguments"],
                                }
                            }
                        ],
                    }
                )

            messages = await process_tool_calls(
                client, model, messages, current_tool_calls, tool_manager, quiet
            )
        else:
            # No tool calls - this is the final response
            final_response = "".join(response_parts)
            if not quiet:
                # Already printed during streaming, just add newline and render Markdown
                print()
                render_markdown(final_response)
            return final_response

    if not quiet:
        print("\n[yellow]⚠ Limite de iterações de tools atingido[/]\n")

    return "".join(response_parts)


def validate_tools_config(enable_tavily: bool, enable_tools: bool) -> None:
    """Validate that tools can be enabled.

    Args:
        enable_tavily: Enable Tavily
        enable_tools: Enable all tools

    Raises:
        SystemExit if configuration is invalid
    """
    if not (enable_tavily or enable_tools):
        return

    if enable_tavily:
        api_key = get_config_value("tavily_api_key")
        if not api_key:
            from miru.renderer import render_error

            render_error(
                "Tavily API key não configurada.",
                "Configure com: miru config set tavily_api_key tvly-sua-key\n"
                "Ou use: export MIRU_TAVILY_API_KEY=tvly-sua-key\n"
                "Obtenha sua key em: https://tavily.com",
            )
            sys.exit(1)
