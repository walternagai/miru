"""miru batch command - process multiple prompts.

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
    Context,
    Format,
    Host,
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
from miru.ollama.client import OllamaClient
from miru.ui.render import render_error

console = Console()


@dataclass
class BatchResult:
    """Result of processing a single prompt."""

    prompt: str
    response: str
    success: bool
    error: str | None = None
    eval_count: int = 0
    eval_duration_ns: int = 0
    total_duration_ns: int = 0
    tokens_per_second: float = 0.0


def _calculate_tokens_per_second(eval_count: int, eval_duration_ns: int) -> float:
    """Calculate tokens per second from evaluation metrics."""
    if eval_duration_ns == 0:
        return 0.0
    eval_seconds = eval_duration_ns / 1e9
    return eval_count / eval_seconds if eval_seconds > 0 else 0.0


def _read_prompts_file(prompt_file: str) -> list[str]:
    """Read prompts from file (one per line or JSONL)."""
    path = Path(prompt_file)

    if not path.exists():
        render_error(t("error.file_not_found", path=prompt_file))
        sys.exit(1)

    if not path.is_file():
        render_error(t("error.file_not_found", path=prompt_file))
        sys.exit(1)

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        render_error(t("error.file_processing", path=prompt_file, error=str(e)))
        sys.exit(1)

    lines = [line.strip() for line in content.split("\n") if line.strip()]

    if not lines:
        render_error("File is empty or contains no valid prompts")
        sys.exit(1)

    # Parse JSONL if lines start with {
    prompts = []
    for line in lines:
        if line.startswith("{"):
            try:
                data = json.loads(line)
                # Try common field names
                prompt = data.get("prompt", data.get("text", data.get("question", str(data))))
                prompts.append(prompt)
            except json.JSONDecodeError:
                prompts.append(line)
        else:
            prompts.append(line)

    return prompts


async def _process_single_prompt(
    client: OllamaClient,
    model: str,
    prompt: str,
    system_prompt: str | None,
    options: dict | None,
    stream: bool,
    quiet: bool,
) -> BatchResult:
    """Process a single prompt and return result."""
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response_parts = []
        final_chunk = None

        if system_prompt:
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
            chunks = client.generate(model, prompt, options=options, stream=stream)
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

            return BatchResult(
                prompt=prompt,
                response=response_text,
                success=True,
                eval_count=eval_count,
                eval_duration_ns=eval_duration_ns,
                total_duration_ns=total_duration_ns,
                tokens_per_second=tokens_per_second,
            )

        return BatchResult(
            prompt=prompt,
            response=response_text,
            success=False,
            error="No final chunk received",
        )

    except Exception:
        return BatchResult(
            prompt=prompt,
            response="",
            success=False,
            error=t("error.model_not_found", model=model),
        )
    except Exception as e:
        return BatchResult(
            prompt=prompt,
            response="",
            success=False,
            error=str(e),
        )


def _render_results_table(results: list[BatchResult], quiet: bool = False) -> None:
    """Render results as table."""
    if quiet:
        return

    from miru.core.i18n import get_language
    lang = get_language()
    
    if lang == "pt_BR":
        title = "Resultados do Batch"
        col_num = "#"
        col_prompt = "Prompt"
        col_status = "Status"
        col_tokens = "Tokens"
        col_time = "Tempo"
        summary = "Resumo:"
        total_label = "Total:"
        success_label = "Sucesso:"
        error_label = "Erro:"
        tokens_label = "Tokens gerados:"
        time_label = "Tempo total:"
        speed_label = "Velocidade média:"
    elif lang == "es_ES":
        title = "Resultados del Batch"
        col_num = "#"
        col_prompt = "Prompt"
        col_status = "Estado"
        col_tokens = "Tokens"
        col_time = "Tiempo"
        summary = "Resumen:"
        total_label = "Total:"
        success_label = "Éxito:"
        error_label = "Error:"
        tokens_label = "Tokens generados:"
        time_label = "Tiempo total:"
        speed_label = "Velocidad media:"
    else:
        title = "Batch Results"
        col_num = "#"
        col_prompt = "Prompt"
        col_status = "Status"
        col_tokens = "Tokens"
        col_time = "Time"
        summary = "Summary:"
        total_label = "Total:"
        success_label = "Success:"
        error_label = "Error:"
        tokens_label = "Tokens generated:"
        time_label = "Total time:"
        speed_label = "Average speed:"

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column(col_num, style="dim", width=4)
    table.add_column(col_prompt, width=40)
    table.add_column(col_status, width=8)
    table.add_column(col_tokens, justify="right")
    table.add_column(col_time, justify="right")

    for idx, result in enumerate(results, start=1):
        prompt_display = result.prompt[:37] + "..." if len(result.prompt) > 40 else result.prompt

        if result.success:
            status = "[green]✓[/]"
            time_str = f"{result.total_duration_ns / 1e9:.1f}s"
            tokens_str = str(result.eval_count)
        else:
            status = "[red]✗[/]"
            time_str = "—"
            tokens_str = "—"

        table.add_row(
            str(idx),
            prompt_display,
            status,
            tokens_str,
            time_str,
        )

    console.print(table)

    # Summary
    success_count = sum(1 for r in results if r.success)
    total_tokens = sum(r.eval_count for r in results if r.success)
    total_time = sum(r.total_duration_ns for r in results if r.success) / 1e9
    avg_tokens_per_sec = total_tokens / total_time if total_time > 0 else 0.0

    console.print()
    console.print(f"[bold]{summary}[/]")
    console.print(f"  {total_label} {len(results)} prompts")
    console.print(f"  {success_label} {success_count} | {error_label} {len(results) - success_count}")
    console.print(f"  {tokens_label} {total_tokens}")
    console.print(f"  {time_label} {total_time:.1f}s")
    console.print(f"  {speed_label} {avg_tokens_per_sec:.1f} tok/s")


def _render_results_json(results: list[BatchResult], model: str) -> None:
    """Render results as JSON."""
    output = {
        "model": model,
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
        "error_count": sum(1 for r in results if not r.success),
        "results": [
            {
                "prompt": r.prompt,
                "response": r.response,
                "success": r.success,
                "error": r.error,
                "metrics": {
                    "eval_count": r.eval_count,
                    "total_duration_ns": r.total_duration_ns,
                    "tokens_per_second": round(r.tokens_per_second, 2),
                }
                if r.success
                else None,
            }
            for r in results
        ],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


def _render_results_jsonl(results: list[BatchResult]) -> None:
    """Render results as JSON Lines."""
    for result in results:
        output = {
            "prompt": result.prompt,
            "response": result.response,
            "success": result.success,
        }
        if result.success:
            output["eval_count"] = result.eval_count
            output["total_duration_ns"] = result.total_duration_ns
            output["tokens_per_second"] = round(result.tokens_per_second, 2)
        else:
            output["error"] = result.error

        print(json.dumps(output, ensure_ascii=False))


async def _batch_async(
    model: str,
    prompts: list[str],
    host: str,
    system_prompt: str | None,
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
    stop_on_error: bool,
    timeout: float | None,
) -> None:
    """Async implementation of batch command."""
    options = build_options(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_tokens=max_tokens,
        seed=seed,
        repeat_penalty=repeat_penalty,
        ctx=ctx,
    )

    results: list[BatchResult] = []
    success_count = 0

    async with OllamaClient(host, timeout=timeout) as client:
        if not quiet and output_format == "text":
            from miru.core.i18n import get_language
            lang = get_language()
            if lang == "pt_BR":
                msg = f"[bold]Processando {len(prompts)} prompts com {model}[/]"
            elif lang == "es_ES":
                msg = f"[bold]Procesando {len(prompts)} prompts con {model}[/]"
            else:
                msg = f"[bold]Processing {len(prompts)} prompts with {model}[/]"
            console.print(msg)
            console.print()

        for idx, prompt in enumerate(prompts, start=1):
            if not quiet and output_format == "text":
                console.print(f"[bold cyan]── [{idx}/{len(prompts)}][/]")
                console.print(f"[dim]Prompt:[/] {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
                console.print()

            result = await _process_single_prompt(
                client=client,
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                options=options,
                stream=not no_stream,
                quiet=quiet or output_format != "text",
            )

            results.append(result)

            if result.success:
                success_count += 1
                if not quiet and output_format == "text":
                    total_seconds = result.total_duration_ns / 1e9
                    console.print(
                        f"[green]✓[/] {result.eval_count} tokens · {total_seconds:.1f}s · {result.tokens_per_second:.1f} tok/s"
                    )
                    console.print()
            else:
                if not quiet and output_format == "text":
                    from miru.core.i18n import t
                    console.print(f"[red]✗ {t('error.prefix')}:[/] {result.error}")
                    console.print()

                if stop_on_error:
                    from miru.core.i18n import get_language
                    lang = get_language()
                    if lang == "pt_BR":
                        msg = "[red bold]Parando devido a erro (stop-on-error)[/]"
                    elif lang == "es_ES":
                        msg = "[red bold]Deteniendo debido a error (stop-on-error)[/]"
                    else:
                        msg = "[red bold]Stopping due to error (stop-on-error)[/]"
                    console.print(msg)
                    break

    if output_format == "json":
        _render_results_json(results, model)
    elif output_format == "jsonl":
        _render_results_jsonl(results)
    else:
        _render_results_table(results, quiet)

    # Exit with error code if any failures
    if success_count == 0:
        sys.exit(1)


def batch(
    model: Annotated[str, typer.Argument(..., help="Model name to use")],
    prompts_file: Annotated[
        str, typer.Option("--prompts", "-p", help="File with prompts (one per line or JSONL)")
    ],
    system: Annotated[
        str | None, typer.Option("--system", "-s", help="System prompt for all prompts")
    ] = None,
    system_file: Annotated[
        str | None, typer.Option("--system-file", help="Read system prompt from file")
    ] = None,
    temperature: Annotated[float | None, typer.Option(help="Sampling temperature")] = None,
    top_p: Annotated[float | None, typer.Option(help="Nucleus sampling probability")] = None,
    top_k: Annotated[int | None, typer.Option(help="Top-k sampling")] = None,
    max_tokens: Annotated[int | None, typer.Option(help="Max tokens to generate")] = None,
    seed: Annotated[int | None, typer.Option(help="Random seed")] = None,
    repeat_penalty: Annotated[float | None, typer.Option(help="Repetition penalty")] = None,
    ctx: Annotated[int | None, typer.Option(help="Context window size")] = None,
    no_stream: Annotated[bool, typer.Option("--no-stream", help="Disable streaming")] = False,
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[
        str, typer.Option("--format", help="Output format (text/json/jsonl)")
    ] = "text",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Minimal output")] = False,
    stop_on_error: Annotated[
        bool, typer.Option("--stop-on-error", help="Stop processing on first error")
    ] = False,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", "-t", help="Request timeout in seconds (default: 30)"),
    ] = None,
) -> None:
    """Process multiple prompts from a file in batch.

    Examples:
        miru batch gemma3:latest --prompts prompts.txt
        miru batch qwen2.5:7b --prompts prompts.jsonl --format json
        miru batch gemma3 --prompts prompts.txt --system "You are helpful" --format jsonl
    """
    if format not in ("text", "json", "jsonl"):
        render_error(t("error.invalid_format", format=format, valid_formats="text, json, jsonl"))
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

    # Read prompts
    prompts = _read_prompts_file(prompts_file)

    resolved_host = resolve_host(host)

    try:
        asyncio.run(
            _batch_async(
                model=model,
                prompts=prompts,
                host=resolved_host,
                system_prompt=final_system_prompt,
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
                stop_on_error=stop_on_error,
                timeout=timeout,
            )
        )
    except KeyboardInterrupt:
        print()
        console.print("[yellow]Interrompido pelo usuário[/]")
        sys.exit(0)
    except OllamaConnectionError as e:
        console.print(f"[red bold]✗[/] {e}")
        sys.exit(1)
