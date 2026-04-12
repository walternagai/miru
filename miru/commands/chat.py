"""Chat command for multi-turn interactive inference.

Refactored version using core module for i18n and errors.
"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from miru.alias import resolve_alias
from miru.cli_options import (
    AudioFile,
    Context,
    EnableTavily,
    EnableTools,
    Host,
    ImageFiles,
    InputFiles,
    MaxTokens,
    ModelOptional,
    Quiet,
    RepeatPenalty,
    SandboxDir,
    Seed,
    SystemPrompt,
    SystemPromptFile,
    Temperature,
    Timeout,
    ToolMode,
    TopK,
    TopP,
    get_model_with_fallback,
)
from miru.core.config import resolve_host
from miru.core.errors import ModelNotFoundError, ConnectionError as MiruConnectionError
from miru.core.i18n import t, set_language
from miru.history import record_history, get_history
from miru.inference_params import build_options
from miru.ollama.client import OllamaClient
from miru.output import stream_as_markdown_live
from miru.ui.prompts import prompt_choice
from miru.ui.render import render_error, render_success

console = Console()


def _print_help() -> None:
    """Print chat commands help."""
    console.print()
    console.print(f"[bold]{t('chat.commands.help')}[/]")
    console.print(f"  /exit, /quit   - {t('chat.commands.exit')}")
    console.print(f"  /clear         - {t('chat.commands.clear')}")
    console.print(f"  /history       - {t('chat.commands.history')}")
    console.print(f"  /stats         - {t('chat.commands.stats')}")
    console.print(f"  /model <name>  - {t('chat.commands.model')}")
    console.print(f"  /system <p>    - {t('chat.commands.system')}")
    console.print(f"  /recall [n]    - {t('chat.commands.recall')}")
    console.print(f"  /retry         - {t('chat.commands.retry')}")
    console.print(f"  /save <file>   - {t('chat.commands.save')}")
    console.print(f"  /help          - {t('chat.commands.help_cmd')}")
    console.print()


async def _chat_async(
    model: str,
    host: str,
    system_prompt: str | None,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    max_tokens: int | None,
    seed: int | None,
    repeat_penalty: float | None,
    ctx: int | None,
    quiet: bool,
    timeout: float | None,
    enable_tools: bool = False,
    enable_tavily: bool = False,
    sandbox_dir: str | None = None,
    tool_mode: str = "auto_safe",
) -> None:
    """Async implementation of chat command."""
    from miru.tool_integration import create_tool_manager, execute_tool_loop, validate_tools_config

    model = resolve_alias(model)

    validate_tools_config(enable_tavily=enable_tavily, enable_tools=enable_tools)

    tool_manager = create_tool_manager(
        enable_tools=enable_tools,
        enable_tavily=enable_tavily,
        sandbox_dir=sandbox_dir,
        tool_mode=tool_mode,
    )

    try:
        async with OllamaClient(host, timeout=timeout) as client:
            all_models = await client.list_models()
            model_names = [m.get("name", "") for m in all_models]
            
            if model not in model_names:
                error = ModelNotFoundError(model, model_names[:5])
                render_error(error.message, error.suggestion)
                sys.exit(1)

            options = build_options(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
            )

            if not quiet:
                print(f"miru chat · {model}")
                if system_prompt:
                    print(f"System: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")
                print(f"{t('prompt.enter')} · /exit {t('chat.commands.exit').lower()}")
                print("─" * 50)

            messages: list[dict[str, str]] = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            turn_count = 0
            total_tokens = 0
            total_time_ns = 0
            last_user_input: str | None = None
            current_model = model
            current_system = system_prompt

            while True:
                try:
                    user_input = input(">>> ")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    if not quiet:
                        print()
                        print("─" * 50)
                        speed_msg = ""
                        if total_tokens > 0 and total_time_ns > 0:
                            avg_speed = total_tokens / (total_time_ns / 1e9)
                            speed_msg = f" · {t('chat.total_tokens', tokens=total_tokens, speed=avg_speed)}"
                        print(f"{t('chat.session_ended', turns=turn_count, model=current_model)}{speed_msg}")
                    sys.exit(0)

                if not user_input.strip():
                    continue

                stripped = user_input.strip()

                if stripped in ("/exit", "/quit"):
                    if not quiet:
                        print("─" * 50)
                        speed_msg = ""
                        if total_tokens > 0 and total_time_ns > 0:
                            avg_speed = total_tokens / (total_time_ns / 1e9)
                            speed_msg = f" · {t('chat.total_tokens', tokens=total_tokens, speed=avg_speed)}"
                        print(f"{t('chat.session_ended', turns=turn_count, model=current_model)}{speed_msg}")
                    break

                if stripped == "/clear":
                    messages = []
                    if current_system:
                        messages.append({"role": "system", "content": current_system})
                    turn_count = 0
                    total_tokens = 0
                    total_time_ns = 0
                    if not quiet:
                        render_success(t("chat.history_cleared"))
                    continue

                if stripped == "/history":
                    if not quiet:
                        print(f"Turn(s): {turn_count}")
                    continue

                if stripped == "/help":
                    _print_help()
                    continue

                if stripped == "/stats":
                    if not quiet:
                        console.print("[bold]Session Stats[/]")
                        console.print(f"  Model: {current_model}")
                        console.print(f"  Turns: {turn_count}")
                        console.print(f"  Tokens: {total_tokens}")
                        if total_time_ns > 0:
                            total_seconds = total_time_ns / 1e9
                            console.print(f"  Time: {total_seconds:.1f}s")
                            avg_speed = total_tokens / total_seconds
                            console.print(f"  Average speed: {avg_speed:.1f} tok/s")
                        if current_system:
                            console.print(f"  System prompt: {current_system[:50]}...")
                    continue

                if stripped.startswith("/model "):
                    new_model = stripped[7:].strip()
                    new_model = resolve_alias(new_model)

                    if new_model not in model_names:
                        console.print(f"[red bold]✗[/] {ModelNotFoundError(new_model, model_names[:5])}")
                        console.print("[dim]Available models: miru list[/]")
                        continue

                    current_model = new_model
                    render_success(t("chat.model_switched", model=current_model))
                    continue

                if stripped.startswith("/system "):
                    new_system = stripped[8:].strip()
                    current_system = new_system
                    messages = [{"role": "system", "content": new_system}] + [
                        m for m in messages if m.get("role") != "system"
                    ]
                    render_success(t("chat.system_updated"))
                    continue

                if stripped.startswith("/recall"):
                    parts = stripped.split(maxsplit=1)
                    entries = get_history(limit=10, command="chat")

                    if not entries:
                        render_error(t("chat.recall_empty"))
                        continue

                    recalled_prompt: str | None = None

                    if len(parts) > 1:
                        # /recall N — load by index and auto-execute
                        try:
                            idx = int(parts[1])
                            if 0 <= idx < len(entries):
                                entry = entries[idx]
                                recalled_prompt = entry.prompt
                                if not quiet:
                                    date_str = entry.timestamp[:16] if len(entry.timestamp) >= 16 else entry.timestamp
                                    render_success(t("chat.recall_loaded", date=date_str))
                                    print(f">>> {recalled_prompt}")
                            else:
                                render_error(f"Index {idx} out of range (0-{len(entries)-1})")
                                continue
                        except ValueError:
                            render_error(f"Invalid index: {parts[1]}")
                            continue
                    else:
                        # /recall — interactive selection
                        from rich.table import Table
                        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
                        table.add_column("#", style="dim cyan", width=4)
                        table.add_column("Data", style="dim", width=16)
                        table.add_column("Prompt")
                        for idx, entry in enumerate(entries):
                            date_str = entry.timestamp[:16] if len(entry.timestamp) >= 16 else entry.timestamp
                            prompt_preview = entry.prompt[:72] + "…" if len(entry.prompt) > 72 else entry.prompt
                            table.add_row(str(idx), date_str, prompt_preview)
                        console.print(f"\n[bold]{t('chat.recall_title')}[/]")
                        console.print(table)
                        console.print(f"\n[dim]{t('chat.recall_prompt', count=len(entries)-1)}[/]")

                        try:
                            selection = input(">>> ").strip()
                            if not selection:
                                continue
                            idx = int(selection)
                            if 0 <= idx < len(entries):
                                entry = entries[idx]
                                recalled_prompt = entry.prompt
                                if not quiet:
                                    date_str = entry.timestamp[:16] if len(entry.timestamp) >= 16 else entry.timestamp
                                    render_success(t("chat.recall_loaded", date=date_str))
                            else:
                                render_error(f"Index {idx} out of range (0-{len(entries)-1})")
                                continue
                        except (ValueError, KeyboardInterrupt, EOFError):
                            continue

                    if recalled_prompt:
                        user_input = recalled_prompt
                        # Fall through to normal message processing below
                    else:
                        continue

                if stripped == "/retry":
                    if last_user_input is None:
                        render_error(t("chat.no_previous_prompt"))
                        continue
                    user_input = last_user_input
                else:
                    last_user_input = user_input

                if stripped.startswith("/save "):
                    filename = stripped[6:].strip()
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(f"# Chat session with {current_model}\n\n")
                            for m in messages:
                                role = m.get("role", "unknown")
                                content = m.get("content", "")
                                f.write(f"## {role.upper()}\n{content}\n\n")
                            f.write(f"## Session Stats\n- Turns: {turn_count}\n- Tokens: {total_tokens}\n")
                        render_success(t("success.session_saved", filename=filename))
                    except Exception as e:
                        render_error(f"Error saving: {e}")
                    continue

                messages.append({"role": "user", "content": user_input})

                if tool_manager:
                    response_text = await execute_tool_loop(
                        client=client,
                        model=current_model,
                        messages=messages,
                        tool_manager=tool_manager,
                        options=options,
                        quiet=quiet,
                    )
                    final_chunk = None
                else:
                    chunks = client.chat(current_model, messages, options=options, stream=True)
                    response_text, final_chunk = await stream_as_markdown_live(
                        chunks, quiet=quiet, show_metrics=not quiet
                    )

                if final_chunk and not quiet:
                    eval_count = final_chunk.get("eval_count", 0)
                    eval_duration_ns = final_chunk.get("eval_duration", 0)
                    total_duration_ns = final_chunk.get("total_duration", 0)

                    duration_ns = eval_duration_ns if eval_duration_ns > 0 else total_duration_ns

                    total_tokens += eval_count
                    total_time_ns += duration_ns

                messages.append({"role": "assistant", "content": response_text})
                turn_count += 1

                record_history(
                    command="chat",
                    model=current_model,
                    prompt=user_input,
                    system_prompt=current_system,
                    response=response_text[:1000],
                    success=True,
                    metrics={"eval_count": final_chunk.get("eval_count", 0) if final_chunk else 0},
                )

    except MiruConnectionError as e:
        render_error(e.message, e.suggestion)
        sys.exit(1)


def chat(
    model: ModelOptional = None,
    system: SystemPrompt = None,
    system_file: SystemPromptFile = None,
    temperature: Temperature = None,
    top_p: TopP = None,
    top_k: TopK = None,
    max_tokens: MaxTokens = None,
    seed: Seed = None,
    repeat_penalty: RepeatPenalty = None,
    ctx: Context = None,
    host: Host = None,
    quiet: Quiet = False,
    timeout: Timeout = None,
    enable_tools: EnableTools = False,
    enable_tavily: EnableTavily = False,
    sandbox_dir: SandboxDir = None,
    tool_mode: ToolMode = "auto_safe",
) -> None:
    """Start interactive chat session.
    
    Chat commands:
        /exit, /quit   - End session
        /clear         - Clear history
        /history       - Show turn count
        /stats         - Show session statistics
        /model <name>  - Switch model
        /system <p>    - Change system prompt
        /recall [n]    - Recall previous prompt (interactive or by index)
        /retry         - Retry last prompt
        /save <file>   - Save conversation
        /help          - Show commands
        
    Tools (Function Calling):
        --enable-tools    Enable all tools (file, system, tavily)
        --tavily          Enable Tavily web search specifically
        --sandbox-dir     Directory for file operations (default: ./.miru_sandbox)
        --tool-mode       Execution mode: manual/auto/auto_safe (default: auto_safe)
        
    Examples:
        miru chat gemma3:latest
        miru chat --system "You are a helpful assistant"
        miru chat qwen2.5:7b --system-file prompt.txt
        miru chat gemma3 --tavily
        miru chat qwen --enable-tools --sandbox-dir ./workspace
    """
    from miru.core.config import get_config

    config = get_config()
    
    # Set language from config
    if config.language:
        set_language(config.language)
    
    # Get model (with fallback to config)
    model = get_model_with_fallback(model)

    # Resolve tool settings from config if not specified via CLI
    from miru.core.config import (
        resolve_enable_tools as _resolve_tools,
        resolve_enable_tavily as _resolve_tavily,
        resolve_tool_mode as _resolve_mode,
        resolve_sandbox_dir as _resolve_sandbox,
    )

    final_enable_tools = enable_tools if enable_tools else _resolve_tools()
    final_enable_tavily = enable_tavily if enable_tavily else _resolve_tavily()
    final_tool_mode = tool_mode if tool_mode != "auto_safe" else _resolve_mode()
    final_sandbox_dir = sandbox_dir if sandbox_dir else _resolve_sandbox()

    if system is not None and system_file is not None:
        render_error("Use --system OR --system-file, not both.")
        sys.exit(1)

    final_system_prompt: str | None = None
    if system_file is not None:
        try:
            system_path = Path(system_file)
            if not system_path.exists():
                render_error(f"File not found: {system_file}")
                sys.exit(1)
            final_system_prompt = system_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            render_error(f"Error reading system prompt file: {e}")
            sys.exit(1)
    elif system is not None:
        final_system_prompt = system.strip()

    resolved_host = resolve_host(host)

    import os
    _tui_disabled = not sys.stdout.isatty() or os.environ.get("MIRU_NO_TUI", "").strip() == "1"

    if not _tui_disabled:
        try:
            from miru.ui.tui.app import TUIApp
            TUIApp(
                model=model,
                host=resolved_host,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                ctx=ctx,
                system_prompt=final_system_prompt,
                timeout=timeout,
                enable_tools=final_enable_tools,
                enable_tavily=final_enable_tavily,
                sandbox_dir=final_sandbox_dir,
                tool_mode=final_tool_mode,
            ).run()
            return
        except ImportError:
            pass  # textual not available, fall through to CLI mode

    try:
        asyncio.run(
            _chat_async(
                model=model,
                host=resolved_host,
                system_prompt=final_system_prompt,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
                quiet=quiet,
                timeout=timeout,
                enable_tools=final_enable_tools,
                enable_tavily=final_enable_tavily,
                sandbox_dir=final_sandbox_dir,
                tool_mode=final_tool_mode,
            )
        )
    except KeyboardInterrupt:
        sys.exit(0)