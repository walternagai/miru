"""Compare command for benchmarking multiple models.

Refactored with i18n support.
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.cli_options import (
    AutoPull,
    Context,
    Format,
    Host,
    ImageFiles,
    MaxTokens,
    Quiet,
    RepeatPenalty,
    Seed,
    SystemPrompt,
    SystemPromptFile,
    Temperature,
    Timeout,
    TopK,
    TopP,
)
from miru.core.config import resolve_host
from miru.core.errors import ModelNotFoundError, ConnectionError as MiruConnectionError
from miru.core.i18n import t
from miru.inference_params import build_options
from miru.input import encode_images
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient
from miru.ui.render import render_error, render_success

console = Console()


@dataclass
class ModelResult:
    """Result of a single model inference."""

    model: str
    prompt: str
    response: str
    eval_count: int
    eval_duration_ns: int
    total_duration_ns: int
    tokens_per_second: float
    error: str | None = None


def _calculate_tokens_per_second(
    eval_count: int, eval_duration_ns: int, total_duration_ns: int = 0
) -> float:
    """Calculate tokens per second from evaluation metrics.

    Args:
        eval_count: Number of tokens generated
        eval_duration_ns: Time spent evaluating in nanoseconds
        total_duration_ns: Total time in nanoseconds (fallback)

    Returns:
        Tokens per second, or 0.0 if cannot calculate
    """
    # Prefer eval_duration for accuracy
    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        return eval_count / eval_seconds if eval_seconds > 0 else 0.0

    # Fallback to total_duration if available
    if total_duration_ns and total_duration_ns > 0:
        total_seconds = total_duration_ns / 1e9
        return eval_count / total_seconds if total_seconds > 0 else 0.0

    return 0.0


async def _execute_model(
    client: OllamaClient,
    model: str,
    prompt: str,
    system_prompt: str | None,
    images: list[str] | None,
    options: dict | None,
    stream: bool,
    quiet: bool,
) -> ModelResult:
    """Execute a single model and return results."""
    response_parts = []
    final_chunk = None

    try:
        # Use chat API when system prompt present, generate otherwise
        if system_prompt:
            messages = []
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            chunks = client.chat(model, messages, options=options, stream=stream)

            async for chunk in chunks:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    response_parts.append(content)
                    if not quiet and stream:
                        print(content, end="", flush=True)

                if chunk.get("done"):
                    final_chunk = chunk
        else:
            chunks = client.generate(model, prompt, images=images, options=options, stream=stream)

            async for chunk in chunks:
                text = chunk.get("response", "")
                if text:
                    response_parts.append(text)
                    if not quiet and stream:
                        print(text, end="", flush=True)

                if chunk.get("done"):
                    final_chunk = chunk

        if not quiet and stream:
            print()

        response_text = "".join(response_parts)

        if final_chunk:
            eval_count = final_chunk.get("eval_count", 0)
            eval_duration_ns = final_chunk.get("eval_duration", 0)
            total_duration_ns = final_chunk.get("total_duration", 0)
            tokens_per_second = _calculate_tokens_per_second(
                eval_count, eval_duration_ns, total_duration_ns
            )

            return ModelResult(
                model=model,
                prompt=prompt,
                response=response_text,
                eval_count=eval_count,
                eval_duration_ns=eval_duration_ns,
                total_duration_ns=total_duration_ns,
                tokens_per_second=tokens_per_second,
                error=None,
            )

        return ModelResult(
            model=model,
            prompt=prompt,
            response=response_text,
            eval_count=0,
            eval_duration_ns=0,
            total_duration_ns=0,
            tokens_per_second=0.0,
            error="No final chunk received",
        )

    except Exception:
        if not quiet and stream:
            print()
        set_language("en_US")
        return ModelResult(
            model=model,
            prompt=prompt,
            response="",
            eval_count=0,
            eval_duration_ns=0,
            total_duration_ns=0,
            tokens_per_second=0.0,
            error=t("error.model_not_found", model=model),
        )
    except Exception as e:
        if not quiet and stream:
            print()
        return ModelResult(
            model=model,
            prompt=prompt,
            response="",
            eval_count=0,
            eval_duration_ns=0,
            total_duration_ns=0,
            tokens_per_second=0.0,
            error=str(e),
        )


def _render_comparison_table(results: list[ModelResult], quiet: bool = False) -> None:
    """Render comparison table at the end."""
    if quiet:
        return

    from miru.core.i18n import get_language
    lang = get_language()
    
    if lang == "pt_BR":
        title = "Comparação de Modelos"
        col_model = "Modelo"
        col_tokens = "Tokens"
        col_time = "Tempo"
        col_speed = "Velocidade"
    elif lang == "es_ES":
        title = "Comparación de Modelos"
        col_model = "Modelo"
        col_tokens = "Tokens"
        col_time = "Tiempo"
        col_speed = "Velocidad"
    else:
        title = "Model Comparison"
        col_model = "Model"
        col_tokens = "Tokens"
        col_time = "Time"
        col_speed = "Speed"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column(col_model, style="green")
    table.add_column(col_tokens, justify="right")
    table.add_column(col_time, justify="right")
    table.add_column(col_speed, justify="right")

    valid_results = [r for r in results if r.error is None]

    if valid_results:
        max_tokens_per_second = max(r.tokens_per_second for r in valid_results)
        min_tokens = min(r.eval_count for r in valid_results)
    else:
        max_tokens_per_second = 0
        min_tokens = 0

    for result in results:
        if result.error:
            table.add_row(
                result.model,
                "— ✗",
                "—",
                "—",
                style="red dim",
            )
        else:
            tokens_str = f"{result.eval_count}"
            if result.eval_count == min_tokens and len(valid_results) > 1:
                tokens_str = f"{result.eval_count} ✓"

            tempo_str = f"{result.total_duration_ns / 1e9:.1f}s"

            speed_str = f"{result.tokens_per_second:.1f} tok/s"
            if result.tokens_per_second == max_tokens_per_second and len(valid_results) > 1:
                speed_str = f"{result.tokens_per_second:.1f} tok/s ✓"
                table.add_row(
                    result.model,
                    tokens_str,
                    tempo_str,
                    speed_str,
                    style="green",
                )
                continue

            table.add_row(
                result.model,
                tokens_str,
                tempo_str,
                speed_str,
            )

    console.print(table)


def _render_seed_warning(quiet: bool, seed: int | None) -> None:
    """Render warning about missing seed."""
    if quiet or seed is not None:
        return

    from miru.core.i18n import get_language
    lang = get_language()
    
    console.print()
    if lang == "pt_BR":
        console.print("[yellow]⚠ Sem --seed: resultados podem variar entre execuções.[/]")
        console.print("  Para comparação reproduzível: miru compare ... --seed 42")
    elif lang == "es_ES":
        console.print("[yellow]⚠ Sin --seed: los resultados pueden variar entre ejecuciones.[/]")
        console.print("  Para comparación reproducible: miru compare ... --seed 42")
    else:
        console.print("[yellow]⚠ Without --seed: results may vary between runs.[/]")
        console.print("  For reproducible comparison: miru compare ... --seed 42")


def _render_json_output(results: list[ModelResult]) -> None:
    """Render JSON output for compare command."""
    output = []
    for result in results:
        entry = {
            "model": result.model,
            "prompt": result.prompt,
            "response": result.response,
            "metrics": {
                "eval_count": result.eval_count,
                "eval_duration_ns": result.eval_duration_ns,
                "total_duration_ns": result.total_duration_ns,
                "tokens_per_second": round(result.tokens_per_second, 1),
            },
            "error": result.error,
        }
        output.append(entry)

    print(json.dumps(output, indent=2))


def _read_prompt_file(prompt_file: str) -> str:
    """Read prompt from file."""
    path = Path(prompt_file)

    if not path.exists():
        render_error(t("error.file_not_found", path=prompt_file))
        sys.exit(1)

    if not path.is_file():
        render_error(t("error.file_not_found", path=prompt_file))
        sys.exit(1)

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        render_error(t("error.file_processing", path=prompt_file, error=str(e)))
        sys.exit(1)


async def _compare_async(
    models: list[str],
    prompt: str,
    system_prompt: str | None,
    host: str,
    images: list[str],
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
    """Async implementation of compare command."""
    results: list[ModelResult] = []

    encoded_images = encode_images(images) if images else None
    options = build_options(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_tokens=max_tokens,
        seed=seed,
        repeat_penalty=repeat_penalty,
        ctx=ctx,
    )

    async with OllamaClient(host) as client:
        for idx, model in enumerate(models, start=1):
            if not quiet and output_format == "text":
                console.print()
                console.print(f"[bold]── [{idx}/{len(models)}] {model}[/] {'─' * 40}")

            if images:
                try:
                    caps = await get_capabilities(client, model)
                    if not caps.supports_vision:
                        error_msg = f"{model} não suporta imagens. Pulando."
                        if not quiet and output_format == "text":
                            console.print(f"[red]✗ {error_msg}[/]")
                        results.append(
                            ModelResult(
                                model=model,
                                prompt=prompt,
                                response="",
                                eval_count=0,
                                eval_duration_ns=0,
                                total_duration_ns=0,
                                tokens_per_second=0.0,
                                error=error_msg,
                            )
                        )
                        continue
                except OllamaModelNotFound:
                    error_msg = f'Modelo "{model}" não encontrado.'
                    if not quiet and output_format == "text":
                        console.print(f"[red]✗ Erro: {error_msg}[/]")
                        console.print(f"  Para baixar: miru pull {model}")
                    results.append(
                        ModelResult(
                            model=model,
                            prompt=prompt,
                            response="",
                            eval_count=0,
                            eval_duration_ns=0,
                            total_duration_ns=0,
                            tokens_per_second=0.0,
                            error=error_msg,
                        )
                    )
                    continue
                except OllamaConnectionError as e:
                    console.print(f"[red bold]✗[/] {e}")
                    sys.exit(1)

            result = await _execute_model(
                client=client,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                images=encoded_images,
                options=options,
                stream=not no_stream,
                quiet=quiet or output_format == "json",
            )
            results.append(result)

            if not quiet and output_format == "text" and result.error is None:
                total_seconds = result.total_duration_ns / 1e9
                console.print(
                    f"✓ {result.eval_count} tokens · {total_seconds:.1f}s · {result.tokens_per_second:.1f} tok/s"
                )

    if output_format == "json":
        _render_json_output(results)
    else:
        console.print()
        _render_comparison_table(results, quiet)
        _render_seed_warning(quiet, seed)

    success_count = sum(1 for r in results if r.error is None)
    if success_count == 0:
        sys.exit(1)


def compare(
    models: Annotated[list[str], typer.Argument(help="Model names to compare (min 2)")],
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Prompt text")] = None,
    prompt_file: Annotated[
        str | None, typer.Option("--prompt-file", "-f", help="Read prompt from file")
    ] = None,
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
        list[str], typer.Option("--file", help="File path to include (repeatable)")
    ] = [],
    audio: Annotated[str | None, typer.Option("--audio", help="Audio file to transcribe")] = None,
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
    """Compare responses from multiple models side by side."""
    if len(models) < 2:
        console.print("[red bold]✗[/] Compare requer ao menos 2 modelos. Exemplo:")
        console.print('  miru compare gemma3:latest qwen2.5:7b --prompt "Sua pergunta"')
        sys.exit(1)

    if prompt is None and prompt_file is None:
        console.print("[red bold]✗[/] É necessário fornecer --prompt ou --prompt-file")
        sys.exit(1)

    if prompt is not None and prompt_file is not None:
        console.print("[red bold]✗[/] Use --prompt OU --prompt-file, não ambos")
        sys.exit(1)

    if format not in ("text", "json"):
        render_error(t("error.invalid_format", format=format, valid_formats="text, json"))
        sys.exit(1)

    # Handle system prompt
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

    final_prompt: str
    if prompt_file:
        final_prompt = _read_prompt_file(prompt_file)
    else:
        final_prompt = prompt or ""

    if file or audio:
        render_error("--file and --audio are not supported in compare command")
        sys.exit(1)

    resolved_host = resolve_host(host)

    try:
        asyncio.run(
            _compare_async(
                models=models,
                prompt=final_prompt,
                system_prompt=final_system_prompt,
                host=resolved_host,
                images=image,
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
            )
        )
    except KeyboardInterrupt:
        print()
        sys.exit(0)
