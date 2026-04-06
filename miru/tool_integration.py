"""Tool integration helpers for chat/run commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from rich.console import Console

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

console = Console()


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

        # Execute tool silently
        result, error = tool_manager.execute_tool(tool_name, arguments)

        if error and not quiet:
            console.print(f"[red bold]Error:[/red bold] {error}\n")

        tool_result_msg = create_tool_result_message(tool_name, result, error)
        messages.append(tool_result_msg)

    return messages


async def generate_query_variations(
    client: OllamaClient,
    model: str,
    original_query: str,
    max_variations: int = 3,
) -> list[str]:
    """Generate search query variations using the model.

    Args:
        client: Ollama client
        model: Model name
        original_query: Original search query
        max_variations: Maximum number of variations to generate

    Returns:
        List of query variations (including original)
    """
    from miru.tools.utils import create_tool_call_message

    prompt = f"""Generate {max_variations} different search queries to find comprehensive information about: "{original_query}"

Rules:
- Each query should approach the topic from a different angle
- Queries should be in the same language as the original
- Return ONLY the queries, one per line, no numbering or explanation
- Make queries specific and search-engine friendly
- Include technical terms, synonyms, and related concepts

Example:
Original: "Python decorators"
Variations:
Python decorators tutorial examples
how do Python decorators work under the hood
Python decorator syntax best practices
common Python decorator patterns"""

    messages_variation = [{"role": "user", "content": prompt}]

    variations = [original_query]

    try:
        chunks = client.chat(model, messages_variation, stream=True)
        response_parts = []

        async for chunk in chunks:
            content = chunk.get("message", {}).get("content", "")
            if content:
                response_parts.append(content)

        variation_text = "".join(response_parts).strip()

        # Parse variations from response
        for line in variation_text.split("\n"):
            line = line.strip()
            # Remove numbering if present
            if line and not line.startswith("#"):
                # Remove common prefixes
                for prefix in ["- ", "* ", "• ", "1. ", "2. ", "3. ", "4. ", "5. "]:
                    if line.startswith(prefix):
                        line = line[len(prefix) :]
                        break
                if line and len(line) > 5:
                    variations.append(line)
                    if len(variations) >= max_variations + 1:  # +1 for original
                        break
    except Exception:
        # If variation generation fails, just use original
        pass

    return variations[: max_variations + 1]


async def enhance_tavily_search(
    client: OllamaClient,
    model: str,
    query: str,
    tool_manager: ToolExecutionManager,
    max_results: int = 5,
) -> tuple[str, Exception | None]:
    """Enhance Tavily search with query variations.

    Args:
        client: Ollama client
        model: Model name
        query: Original search query
        tool_manager: Tool execution manager
        max_results: Results per query

    Returns:
        Tuple of (combined_results, error)
    """
    # Generate query variations
    variations = await generate_query_variations(client, model, query, max_variations=2)

    all_results = []
    seen_urls = set()

    for search_query in variations:
        result, error = tool_manager.execute_tool(
            "tavily_search", {"query": search_query, "max_results": max_results}
        )

        if error:
            return "", error

        # Parse and deduplicate results
        if result and result not in all_results:
            all_results.append(result)

    # Combine unique results
    combined = "\n\n---\n\n".join(all_results)
    return combined, None


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

    # Show progress indicator during tool execution
    if not quiet:
        import asyncio
        import sys

        async def show_progress():
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            idx = 0
            while True:
                sys.stdout.write(f"\r{chars[idx % len(chars)]} Processando...")
                sys.stdout.flush()
                await asyncio.sleep(0.1)
                idx += 1

        progress_task = asyncio.create_task(show_progress())

        try:
            for iteration in range(max_iterations):
                chunks = client.chat_with_tools(
                    model, messages, tools=tools, options=options, stream=True
                )

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

                if current_tool_calls:
                    for call in current_tool_calls:
                        tool_name = call.get("name", "")
                        arguments = call.get("arguments", {})

                        # Enhance Tavily search with query variations
                        if tool_name == "tavily_search" and "query" in arguments:
                            enhanced_result, error = await enhance_tavily_search(
                                client, model, arguments["query"], tool_manager, max_results=5
                            )
                            if error:
                                result, error = tool_manager.execute_tool(tool_name, arguments)
                            else:
                                result = enhanced_result
                        else:
                            result, error = tool_manager.execute_tool(tool_name, arguments)

                        messages.append(
                            {
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
                        )

                        tool_result_msg = create_tool_result_message(tool_name, result, error)
                        messages.append(tool_result_msg)
                else:
                    # No tool calls - this is the final response
                    sys.stdout.write("\r" + " " * 30 + "\r")
                    sys.stdout.flush()
                    final_response = "".join(response_parts)
                    render_markdown(final_response)
                    return final_response
        finally:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        sys.stdout.write("\r" + " " * 30 + "\r")
        sys.stdout.flush()
        console.print("\n[yellow]⚠ Limite de iterações de tools atingido[/]\n")
        return "".join(response_parts)
    else:
        # Quiet mode - no progress indicator
        for iteration in range(max_iterations):
            chunks = client.chat_with_tools(
                model, messages, tools=tools, options=options, stream=True
            )

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

            if current_tool_calls:
                for call in current_tool_calls:
                    tool_name = call.get("name", "")
                    arguments = call.get("arguments", {})

                    # Enhance Tavily search with query variations
                    if tool_name == "tavily_search" and "query" in arguments:
                        enhanced_result, error = await enhance_tavily_search(
                            client, model, arguments["query"], tool_manager, max_results=5
                        )
                        if error:
                            result, error = tool_manager.execute_tool(tool_name, arguments)
                        else:
                            result = enhanced_result
                    else:
                        result, error = tool_manager.execute_tool(tool_name, arguments)

                    messages.append(
                        {
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
                    )

                    tool_result_msg = create_tool_result_message(tool_name, result, error)
                    messages.append(tool_result_msg)
            else:
                # No tool calls - this is the final response
                final_response = "".join(response_parts)
                return final_response


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
