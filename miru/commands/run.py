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
from miru.output import collect_stream, render_json_output, render_metrics


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
) -> None:
    """Async implementation of run command."""
    model = resolve_alias(model)

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

            if system_prompt:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": final_prompt})

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

                    response_parts = []
                    final_chunk = None

                    async for chunk in chunks:
                        if not quiet:
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                response_parts.append(content)
                        else:
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                response_parts.append(content)

                        if chunk.get("done"):
                            final_chunk = chunk

                    if not quiet:
                        print()
                        if final_chunk:
                            render_metrics(final_chunk)
                    else:
                        print("".join(response_parts), end="")
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

                    response_parts = []
                    final_chunk = None

                    async for chunk in chunks:
                        if not quiet:
                            text = chunk.get("response", "")
                            if text:
                                print(text, end="", flush=True)
                                response_parts.append(text)
                        else:
                            text = chunk.get("response", "")
                            if text:
                                response_parts.append(text)

                        if chunk.get("done"):
                            final_chunk = chunk

                    if not quiet:
                        print()
                        if final_chunk:
                            render_metrics(final_chunk)
                    else:
                        print("".join(response_parts), end="")

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
) -> None:
    """Generate text with a single prompt.

    Examples:
        miru run gemma3:latest "Explain recursion"
        miru run llava:latest "Describe" --image photo.jpg
        miru run qwen2.5 --system "Be concise" "What is Python?"
    """
    if format not in ("text", "json"):
        from miru.renderer import render_error

        render_error(f"Invalid format: {format}. Use 'text' or 'json'.")
        sys.exit(1)

    model = resolve_alias(model)

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
            )
        )
    except KeyboardInterrupt:
        print()
        sys.exit(0)
