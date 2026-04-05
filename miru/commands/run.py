"""Run command for single prompt inference."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer

from miru.config import get_host
from miru.inference_params import build_options
from miru.input import encode_images, extract_file_content, transcribe_audio
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.output import collect_stream, render_json_output, render_metrics


async def _run_async(
    model: str,
    prompt: str,
    host: str,
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
) -> None:
    """Async implementation of run command."""
    async with OllamaClient(host) as client:
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
                        f"Modelos com visão disponíveis localmente:\n"
                        + "\n".join(f"    • {m}" for m in vision_models)
                        + f"\n  Use: miru run {vision_models[0] if vision_models else 'llava:latest'} \"<prompt>\" --image <arquivo>"
                        if vision_models else
                        "Nenhum modelo com visão disponível. Use: miru pull llava:latest"
                    )
                    sys.exit(1)

                encoded_images = encode_images(images)

            final_prompt = prompt

            context_parts = []
            
            if audio:
                try:
                    transcription = transcribe_audio(audio)
                    context_parts.append(f"[Transcrição de áudio]\n{transcription}\n")
                except FileNotFoundError as e:
                    from miru.renderer import render_error
                    render_error(str(e))
                    sys.exit(1)
                except ValueError as e:
                    from miru.renderer import render_error
                    render_error(str(e))
                    sys.exit(1)

            for file_path in files:
                try:
                    filename = Path(file_path).name
                    content = extract_file_content(file_path)
                    context_parts.append(f"[Conteúdo de {filename}]\n{content}\n[Fim de {filename}]")
                except FileNotFoundError as e:
                    from miru.renderer import render_error
                    render_error(str(e))
                    sys.exit(1)
                except ValueError as e:
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

            if output_format == "json" or no_stream:
                response_text, final_chunk, model_name = await collect_stream(
                    client.generate(model, final_prompt, images=encoded_images, options=options, stream=False)
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
                chunks = client.generate(model, final_prompt, images=encoded_images, options=options, stream=True)
                
                response_parts = []
                final_chunk = None
                model_name = None

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
                        if "model" in chunk:
                            model_name = chunk.get("model")

                if not quiet:
                    print()
                    if final_chunk:
                        render_metrics(final_chunk)
                else:
                    print("".join(response_parts), end="")

        except OllamaModelNotFound:
            from miru.renderer import render_error
            render_error(
                f'Modelo "{model}" não encontrado.',
                f"Para baixar: miru pull {model}"
            )
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error
            render_error(str(e))
            sys.exit(1)


def run(
    model: str,
    prompt: str,
    image: Annotated[list[str], typer.Option("--image", "-i", help="Image file path (repeatable)")] = [],
    file: Annotated[list[str], typer.Option("--file", "-f", help="File path to include (repeatable)")] = [],
    audio: Annotated[str | None, typer.Option("--audio", "-a", help="Audio file to transcribe")] = None,
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
) -> None:
    """Generate text with a single prompt."""
    if format not in ("text", "json"):
        from miru.renderer import render_error
        render_error(f"Invalid format: {format}. Use 'text' or 'json'.")
        sys.exit(1)

    resolved_host = get_host(host)

    try:
        asyncio.run(_run_async(
            model=model,
            prompt=prompt,
            host=resolved_host,
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
        ))
    except KeyboardInterrupt:
        print()
        sys.exit(0)