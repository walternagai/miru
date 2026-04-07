"""Run command for single prompt inference.

Refactored with i18n support and core/ui modules.
"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer

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
    Model,
    Prompt,
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
)
from miru.core.config import resolve_host
from miru.core.errors import ModelNotFoundError, ConnectionError as MiruConnectionError
from miru.core.i18n import t
from miru.history import record_history
from miru.inference_params import build_options
from miru.input import encode_images, extract_text, format_for_prompt, transcribe
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient
from miru.output import collect_stream, render_json_output, render_metrics, render_stream_as_markdown
from miru.ui.render import render_error


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

    try:
        async with OllamaClient(host, timeout=timeout) as client:
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

                    models_list = "\n".join(f"    • {m}" for m in vision_models[:5])
                    if len(vision_models) > 5:
                        models_list += f"\n    ... and {len(vision_models) - 5} more"
                    
                    suggestion = t(
                        "suggestion.available_vision_models",
                        models=models_list
                    ) if vision_models else t("suggestion.pull_vision_model")
                    
                    if vision_models:
                        suggestion += f"\n\n{t('suggestion.use_vision_model', model=vision_models[0])}"
                    
                    render_error(t("error.model_no_vision", model=model), suggestion)
                    sys.exit(1)

                encoded_images = encode_images(images)

            final_prompt = prompt
            context_parts = []

            if audio:
                try:
                    transcription = transcribe(audio)
                    context_parts.append(f"[{t('audio.transcription')}]\n{transcription}\n")
                except Exception as e:
                    render_error(t("error.audio_processing", file=audio, error=str(e)))
                    sys.exit(1)

            for file_path in files:
                try:
                    filename, content = extract_text(file_path)
                    context_parts.append(format_for_prompt(filename, content))
                except FileNotFoundError:
                    render_error(t("error.file_not_found", path=file_path))
                    sys.exit(1)
                except Exception as e:
                    render_error(t("error.file_processing", path=file_path, error=str(e)))
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

    except Exception as e:
        if "OllamaModelNotFound" in str(type(e).__name__):
            all_models = []
            try:
                async with OllamaClient(host) as client:
                    models = await client.list_models()
                    all_models = [m.get("name", "") for m in models[:5]]
            except Exception:
                pass
            
            error = ModelNotFoundError(model, all_models)
            render_error(error.message, error.suggestion)
            sys.exit(1)
        
        if "OllamaConnectionError" in str(type(e).__name__):
            error = MiruConnectionError(host)
            render_error(error.message, error.suggestion)
            sys.exit(1)
        
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
    model: Model,
    prompt: Prompt,
    system: SystemPrompt = None,
    system_file: SystemPromptFile = None,
    image: ImageFiles = [],
    file: InputFiles = [],
    audio: AudioFile = None,
    temperature: Temperature = None,
    top_p: TopP = None,
    top_k: TopK = None,
    max_tokens: MaxTokens = None,
    seed: Seed = None,
    repeat_penalty: RepeatPenalty = None,
    ctx: Context = None,
    no_stream: Annotated[bool, typer.Option("--no-stream", help="Disable streaming")] = False,
    host: Host = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (text/json)")] = "text",
    quiet: Quiet = False,
    auto_pull: Annotated[bool, typer.Option("--auto-pull", help="Auto-download model if missing")] = False,
    timeout: Timeout = None,
    enable_tools: EnableTools = False,
    enable_tavily: EnableTavily = False,
    sandbox_dir: SandboxDir = None,
    tool_mode: ToolMode = "auto_safe",
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
        render_error(t("error.invalid_format", format=format, valid_formats="text, json"))
        sys.exit(1)

    model = resolve_alias(model)

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

    final_system_prompt: str | None = None
    if system is not None and system_file is not None:
        render_error("Use --system OR --system-file, not both.")
        sys.exit(1)

    if system_file is not None:
        try:
            system_path = Path(system_file)
            if not system_path.exists():
                render_error(t("error.file_not_found", path=system_file))
                sys.exit(1)
            final_system_prompt = system_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            render_error(t("error.system_prompt_file", error=str(e)))
            sys.exit(1)
    elif system is not None:
        final_system_prompt = system.strip()

    resolved_host = resolve_host(host)

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