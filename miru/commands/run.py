"""Run command for single prompt inference."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer

from miru.alias import resolve_alias
from miru.config import get_host
from miru.history import record_history
from miru.inference_params import build_options
from miru.input import encode_images, extract_text, format_for_prompt, transcribe
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.output import (
    collect_stream,
    render_json_output,
    render_metrics,
    render_stream_as_markdown,
)


async def _run_async(
    model: str,
    prompt: str,
    host: str,
    system_prompt: str | None,
    images: list[str],
    files: list[str],
    audio: str | None,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    max_tokens: int | None,
    seed: int | None,
    repeat_penalty: float | None,
    ctx: int | None,
    no_stream: bool,
    output_format: str,
    quiet: bool,
    timeout: float | None,
    enable_tools: bool,
    enable_tavily: bool,
    sandbox_dir: str | None,
    tool_mode: str,
) -> None:
    """Async implementation of run command."""
    from miru.tool_integration import create_tool_manager, execute_tool_loop, validate_tools_config

    model = resolve_alias(model)

    validate_tools_config(enable_tavily=enable_tavily, enable_tools=enable_tools)

    tool_manager = create_tool_manager(
        enable_tools=enable_tools,
        enable_tavily=enable_tavily,
        sandbox_dir=sandbox_dir,
        tool_mode=tool_mode,
    )

    async with OllamaClient(host, timeout=timeout) as client:
        try:
            encoded_images: list[str] | None = None
            if images:
                caps = await get_capabilities(client, model)
                if not caps.supports_vision:
                    all_models = await client.list_models()
                    vision_models = []
                    for m in all_models:
                        try:
                            m_caps = await get_capabilities(client, m.get("name", ""))
                            if m_caps.supports_vision:
                                vision_models.append(m.get("name", ""))
                        except Exception:
                            pass

                    from miru.renderer import render_error

                    render_error(
                        f"{model} não suporta imagens.",
                        "Modelos com visão disponíveis localmente:\n"
                        + "\n".join(f"    • {m}" for m in vision_models)
                        + f'\n  Use: miru run {vision_models[0] if vision_models else "llava:latest"} "<prompt>" --image <arquivo>'
                        if vision_models
                        else "Nenhum modelo com visão disponível. Use: miru pull llava:latest",
                    )
                    sys.exit(1)

                encoded_images = encode_images(images)

            final_prompt = prompt

            context_parts = []

            if audio:
                try:
                    transcription = transcribe(audio)
                    context_parts.append(f"[Transcrição de áudio]\n{transcription}\n")
                except Exception as e:
                    from miru.renderer import render_error

                    render_error(str(e))
                    sys.exit(1)

            for file_path in files:
                try:
                    filename, content = extract_text(file_path)
                    context_parts.append(format_for_prompt(filename, content))
                except FileNotFoundError as e:
                    from miru.renderer import render_error

                    render_error(str(e))
                    sys.exit(1)
                except Exception as e:
                    from miru.renderer import render_error

                    render_error(str(e))
                    sys.exit(1)

            if context_parts:
                final_prompt = "\n\n".join(context_parts) + "\n\n" + prompt

            options = build_options(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
            )

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": final_prompt})

            if tool_manager:
                tools = tool_manager.get_tool_definitions()
                from miru.tool_integration import execute_tool_loop

                response_text = await execute_tool_loop(
                    client=client,
                    model=model,
                    messages=messages,
                    tool_manager=tool_manager,
                    options=options,
                    quiet=quiet,
                )
            elif system_prompt:
                if output_format == "json" or no_stream:
                    response_text, final_chunk, model_name = await _collect_chat_stream(
                        client.chat(model, messages, options=options, stream=False)
                    )

                    if output_format == "json":
                        render_json_output(model, prompt, response_text, final_chunk)
                    else:
                        if not quiet:
                            print(response_text)
                            if final_chunk:
                                render_metrics(final_chunk)
                        else:
                            print(response_text)
                else:
                    chunks = client.chat(model, messages, options=options, stream=True)
                    await render_stream_as_markdown(chunks, quiet=quiet, show_metrics=True)
            else:
                if output_format == "json" or no_stream:
                    response_text, final_chunk, model_name = await collect_stream(
                        client.generate(
                            model,
                            final_prompt,
                            images=encoded_images,
                            options=options,
                            stream=False,
                        )
                    )

                    if output_format == "json":
                        render_json_output(model, prompt, response_text, final_chunk)
                    else:
                        if not quiet:
                            print(response_text)
                            if final_chunk:
                                render_metrics(final_chunk)
                        else:
                            print(response_text)
                else:
                    chunks = client.generate(
                        model, final_prompt, images=encoded_images, options=options, stream=True
                    )
                    await render_stream_as_markdown(chunks, quiet=quiet, show_metrics=True)

            record_history(
                command="run",
                model=model,
                prompt=prompt[:500] if prompt else "",
                system_prompt=system_prompt[:200] if system_prompt else None,
                response=None,
                success=True,
            )

        except OllamaModelNotFound:
            from miru.renderer import render_error

            render_error(f'Modelo "{model}" não encontrado.', f"Para baixar: miru pull {model}")
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error

            render_error(str(e))
            sys.exit(1)


async def _collect_chat_stream(stream):
    """Collect chat stream into response text."""
    response_parts = []
    final_chunk = None
    model_name = None

    async for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            response_parts.append(content)

        if chunk.get("done"):
            final_chunk = chunk

    return "".join(response_parts), final_chunk, model_name


def run(
    model: str,
    prompt: str,
    system: Annotated[
        str | None, typer.Option("--system", "-s", help="System prompt to set model behavior")
    ] = None,
    system_file: Annotated[
        str | None, typer.Option("--system-file", help="Read system prompt from file")
    ] = None,
    image: Annotated[
        list[str], typer.Option("--image", "-i", help="Image file path (repeatable)")
    ] = [],
    file: Annotated[
        list[str], typer.Option("--file", "-f", help="File path to include (repeatable)")
    ] = [],
    audio: Annotated[
        str | None, typer.Option("--audio", "-a", help="Audio file to transcribe")
    ] = None,
    temperature: Annotated[float | None, typer.Option(help="Sampling temperature")] = None,
    top_p: Annotated[float | None, typer.Option(help="Nucleus sampling probability")] = None,
    top_k: Annotated[int | None, typer.Option(help="Top-k sampling")] = None,
    max_tokens: Annotated[int | None, typer.Option(help="Max tokens to generate")] = None,
    seed: Annotated[int | None, typer.Option(help="Random seed")] = None,
    repeat_penalty: Annotated[float | None, typer.Option(help="Repetition penalty")] = None,
    ctx: Annotated[int | None, typer.Option(help="Context window size")] = None,
    no_stream: Annotated[bool, typer.Option("--no-stream", help="Disable streaming")] = False,
    host: Annotated[str | None, typer.Option(help="Ollama host URL")] = None,
    format: Annotated[str, typer.Option(help="Output format (text/json)")] = "text",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Minimal output")] = False,
    auto_pull: Annotated[
        bool, typer.Option("--auto-pull", help="Auto-download model if missing")
    ] = False,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", "-t", help="Request timeout in seconds (default: 30)"),
    ] = None,
    enable_tools: Annotated[
        bool, typer.Option("--enable-tools", help="Enable all tools (file, system, tavily)")
    ] = False,
    enable_tavily: Annotated[
        bool, typer.Option("--tavily", help="Enable Tavily web search tool")
    ] = False,
    sandbox_dir: Annotated[
        str | None, typer.Option("--sandbox-dir", help="Sandbox directory for file tools")
    ] = None,
    tool_mode: Annotated[
        str, typer.Option("--tool-mode", help="Tool execution mode (manual/auto/auto_safe)")
    ] = "auto_safe",
) -> None:
    """Generate text with a single prompt.

    Tools (Function Calling):
        --enable-tools    Enable all tools (file, system, tavily)
        --tavily          Enable Tavily web search specifically
        --sandbox-dir     Directory for file operations (default: ./.miru_sandbox)
        --tool-mode       Execution mode: manual/auto/auto_safe (default: auto_safe)

    \b
    Examples:
        miru run gemma3:latest "Explain recursion"
        miru run llava:latest "Describe" --image photo.jpg
        miru run qwen2.5 --system "Be concise" "What is Python?"
        miru run gemma3 --tavily "What are the latest Python features?"
        miru run qwen --enable-tools "Search for Python 3.13 and save to file"
    """
    if format not in ("text", "json"):
        from miru.renderer import render_error

        render_error(f"Invalid format: {format}. Use 'text' or 'json'.")
        sys.exit(1)

    model = resolve_alias(model)

    # Resolve tool settings from config if not specified via CLI
    from miru.config_manager import (
        resolve_enable_tools,
        resolve_enable_tavily,
        resolve_tool_mode,
        resolve_sandbox_dir,
    )

    # Use config values if CLI params are at defaults
    final_enable_tools = enable_tools if enable_tools else resolve_enable_tools()
    final_enable_tavily = enable_tavily if enable_tavily else resolve_enable_tavily()
    final_tool_mode = tool_mode if tool_mode != "auto_safe" else resolve_tool_mode()
    final_sandbox_dir = sandbox_dir if sandbox_dir else resolve_sandbox_dir()

    final_system_prompt: str | None = None
    if system is not None and system_file is not None:
        from miru.renderer import render_error

        render_error("Use --system OU --system-file, não ambos.")
        sys.exit(1)

    if system_file is not None:
        try:
            system_path = Path(system_file)
            if not system_path.exists():
                from miru.renderer import render_error

                render_error(f"Arquivo não encontrado: {system_file}")
                sys.exit(1)
            final_system_prompt = system_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            from miru.renderer import render_error

            render_error(f"Erro ao ler arquivo de system prompt: {e}")
            sys.exit(1)
    elif system is not None:
        final_system_prompt = system.strip()

    resolved_host = get_host(host)

    try:
        asyncio.run(
            _run_async(
                model=model,
                prompt=prompt,
                host=resolved_host,
                system_prompt=final_system_prompt,
                images=image,
                files=file,
                audio=audio,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
                no_stream=no_stream,
                output_format=format,
                quiet=quiet,
                timeout=timeout,
                enable_tools=final_enable_tools,
                enable_tavily=final_enable_tavily,
                sandbox_dir=final_sandbox_dir,
                tool_mode=final_tool_mode,
            )
        )
    except KeyboardInterrupt:
        print()
        sys.exit(0)
