"""Compare command for benchmarking multiple models."""

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.config import get_host
from miru.inference_params import build_options
from miru.input import encode_images
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound

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


def _calculate_tokens_per_second(eval_count: int, eval_duration_ns: int) -> float:
    """Calculate tokens per second from evaluation metrics."""
    if eval_duration_ns == 0:
        return 0.0
    eval_seconds = eval_duration_ns / 1e9
    return eval_count / eval_seconds if eval_seconds > 0 else 0.0


async def _execute_model(
    client: OllamaClient,
    model: str,
    prompt: str,
    images: list[str] | None,
    options: dict | None,
    stream: bool,
    quiet: bool,
) -> ModelResult:
    """Execute a single model and return results."""
    response_parts = []
    final_chunk = None

    try:
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
            tokens_per_second = _calculate_tokens_per_second(eval_count, eval_duration_ns)

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

    except OllamaModelNotFound:
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
            error=f'Modelo "{model}" não encontrado.',
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

    table = Table(title="Comparação de Modelos", show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Tokens", justify="right")
    table.add_column("Tempo", justify="right")
    table.add_column("Velocidade", justify="right")

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

    console.print()
    console.print("[yellow]⚠ Sem --seed: resultados podem variar entre execuções.[/]")
    console.print("  Para comparação reproduzível: miru compare ... --seed 42")


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
        console.print(f"[red bold]✗[/] Arquivo não encontrado: {prompt_file}")
        sys.exit(1)

    if not path.is_file():
        console.print(f"[red bold]✗[/] Não é um arquivo: {prompt_file}")
        sys.exit(1)

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red bold]✗[/] Erro ao ler arquivo: {e}")
        sys.exit(1)


async def _compare_async(
    models: list[str],
    prompt: str,
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
    prompt_file: Annotated[str | None, typer.Option("--prompt-file", "-f", help="Read prompt from file")] = None,
    image: Annotated[list[str], typer.Option("--image", "-i", help="Image file path (repeatable)")] = [],
    file: Annotated[list[str], typer.Option("--file", help="File path to include (repeatable)")] = [],
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
        console.print(f"[red bold]✗[/] Formato inválido: {format}. Use 'text' ou 'json'.")
        sys.exit(1)

    final_prompt: str
    if prompt_file:
        final_prompt = _read_prompt_file(prompt_file)
    else:
        final_prompt = prompt or ""

    if file or audio:
        console.print("[red bold]✗[/] --file e --audio não são suportados no comando compare")
        sys.exit(1)

    resolved_host = get_host(host)

    try:
        asyncio.run(
            _compare_async(
                models=models,
                prompt=final_prompt,
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