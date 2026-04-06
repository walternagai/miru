"""Renderer module for terminal output formatting using Rich."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

if TYPE_CHECKING:
    pass

console = Console()
console_stderr = Console(stderr=True)


def format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable format (GB/MB/KB).

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "5.0 GB", "500 MB")
    """
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def format_date(date_str: str) -> str:
    """
    Format ISO date string to local date.

    Args:
        date_str: ISO date string (e.g., "2026-04-01T12:00:00Z")

    Returns:
        Local date string (e.g., "2026-04-01")
    """
    if not date_str:
        return "-"
    try:
        if "T" in date_str:
            return date_str.split("T")[0]
        return date_str[:10]
    except (ValueError, IndexError):
        return date_str


async def stream_tokens(
    chunks: AsyncIterator[dict],
    quiet: bool = False,
) -> AsyncIterator[dict]:
    """
    Consume chunks from Ollama client generator, display tokens progressively,
    and re-yield each chunk for caller to collect metrics.

    Args:
        chunks: Async iterator of response chunks
        quiet: If True, suppress all token output

    Yields:
        Each chunk from the iterator, including final done chunk
    """
    async for chunk in chunks:
        if not quiet:
            text = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
            if text:
                print(text, end="", flush=True)

        yield chunk

        if chunk.get("done") and not quiet:
            render_metrics(chunk)


def render_metrics(chunk: dict, quiet: bool = False) -> None:
    """
    Display metrics line at end of generation.

    Args:
        chunk: Final done chunk with metrics
        quiet: If True, suppress output
    """
    if quiet:
        return

    eval_count = chunk.get("eval_count", 0)
    total_duration_ns = chunk.get("total_duration", 0)
    eval_duration_ns = chunk.get("eval_duration", 0)

    # Also check for prompt_eval_duration which might be relevant
    prompt_eval_duration_ns = chunk.get("prompt_eval_duration", 0)

    total_seconds = total_duration_ns / 1e9 if total_duration_ns else 0.0

    # Calculate tokens per second using eval_duration if available
    # Otherwise use total_duration as fallback
    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
    elif total_duration_ns and total_duration_ns > 0:
        # Fallback: use total_duration for rate calculation
        # This includes prompt processing time so it's less accurate
        tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
        # If we got zero but have tokens, show a dash
        if tokens_per_second == 0.0 and eval_count > 0:
            tokens_per_second = 0.0
    else:
        tokens_per_second = 0.0

    # Format output
    if tokens_per_second > 0:
        print(f"✓ {eval_count} tokens · {total_seconds:.1f}s · {tokens_per_second:.1f} tok/s")
    else:
        print(f"✓ {eval_count} tokens · {total_seconds:.1f}s")


def render_error(message: str, hint: str | None = None) -> None:
    """
    Display error message in stderr.

    Format: ✗ {message}\n  {hint}

    Args:
        message: Error message
        hint: Optional action hint
    """
    console_stderr.print(f"[red bold]✗[/] {message}")
    if hint:
        console_stderr.print(f"  {hint}")


def render_warning(message: str) -> None:
    """
    Display warning message in stderr.

    Format: ⚠ {message}

    Args:
        message: Warning message
    """
    console_stderr.print(f"[yellow]⚠[/] {message}")


def render_model_table(models: list[dict], quiet: bool = False) -> None:
    """
    Display Rich table with available models.

    Alias for render_models_table for backward compatibility.

    Args:
        models: List of model dicts from /api/tags
        quiet: If True, output only names (one per line)
    """
    _render_models_table_internal(models, quiet)


def render_models_table(models: list[dict], quiet: bool = False) -> None:
    """
    Display Rich table with available models.

    Args:
        models: List of model dicts from /api/tags
        quiet: If True, output only names (one per line)
    """
    _render_models_table_internal(models, quiet)


def _render_models_table_internal(models: list[dict], quiet: bool = False) -> None:
    if not models:
        console.print("[yellow]Nenhum modelo instalado.[/] Use: [bold]miru pull <model>[/]")
        return

    if quiet:
        for model in models:
            print(model.get("name", ""))
        return

    table = Table(title="Modelos disponíveis", show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Tamanho", justify="right")
    table.add_column("Modificado", justify="center")

    for model in models:
        name = model.get("name", "-")
        size = model.get("size", 0)
        modified = model.get("modified_at", "")

        table.add_row(
            name,
            format_size(size),
            format_date(modified),
        )

    console.print(table)
    count = len(models)
    console.print(f"\n{count} modelo(s) disponível(is)")


def render_empty_models() -> None:
    """Display empty models list message."""
    console.print("[yellow]Nenhum modelo instalado.[/] Use: [bold]miru pull <model>[/]")


def render_model_info(
    model_name: str,
    data: dict,
    capabilities: dict,
    quiet: bool = False,
) -> None:
    """
    Display model information as Rich panel.

    Args:
        model_name: Model name
        data: Full model data from /api/show
        capabilities: Capabilities dict from get_capabilities
        quiet: If True, output minimal format
    """
    if quiet:
        print(f"{model_name}")
        return

    details = data.get("details", {})
    families = details.get("families", [])
    parameter_size = details.get("parameter_size", "unknown")
    quantization = details.get("quantization_level", "unknown")

    content_lines = []

    content_lines.append("[bold]Identificação[/]")
    content_lines.append(f"  Família(s)      {', '.join(families) if families else '-'}")
    content_lines.append(f"  Parâmetros      {parameter_size}")
    content_lines.append(f"  Quantização     {quantization}")
    content_lines.append("")

    content_lines.append("[bold]Capacidades[/]")
    supports_vision = capabilities.get("supports_vision", False)
    vision_emoji = "🖼" if supports_vision else "○"
    vision_text = "sim" if supports_vision else "não"
    content_lines.append(f"  {vision_emoji} Suporte a imagens   {vision_text}")

    max_context = capabilities.get("max_context", 2048)
    content_lines.append(f"  📐 Contexto máximo     {max_context:,} tokens")
    content_lines.append("")

    parameters_str = data.get("parameters", "")
    if parameters_str:
        params = _parse_parameters(parameters_str)
        if params:
            content_lines.append("[bold]Parâmetros padrão[/]")
            for key, value in params.items():
                content_lines.append(f"  {key}    {value}")

    content = "\n".join(content_lines)
    panel = Panel(content, title=model_name, border_style="cyan")
    console.print(panel)


def _parse_parameters(params_str: str) -> dict[str, str]:
    """
    Parse parameters string into dict.

    Args:
        params_str: Parameters string (e.g., "num_ctx\\t4096\\nnum_batch\\t512")

    Returns:
        Dict of parameter name -> value
    """
    params = {}
    for line in params_str.split("\n"):
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                params[parts[0]] = parts[1]
    return params


async def render_pull_progress(
    chunks: AsyncIterator[dict],
    model: str,
    quiet: bool = False,
) -> AsyncIterator[dict]:
    """
    Consume pull chunks and display visual progress.
    Re-yields each chunk.

    Args:
        chunks: Async iterator of progress chunks
        model: Model name being pulled
        quiet: If True, minimal output

    Yields:
        Each progress chunk
    """
    progress = None
    task_id = None
    current_status = None

    try:
        async for chunk in chunks:
            status = chunk.get("status", "")

            if quiet:
                if status == "success":
                    print("✓ Concluído.")
            else:
                if status == "pulling manifest":
                    console.print("Obtendo manifesto...")
                elif status == "downloading":
                    if progress is None:
                        progress = create_progress_bar()
                        progress.start()
                        task_id = progress.add_task("Baixando", total=None)

                    completed = chunk.get("completed", 0)
                    total = chunk.get("total", 0)

                    if total and total > 0:
                        progress.update(task_id, completed=completed, total=total)
                    else:
                        progress.update(task_id, completed=completed)

                elif status == "verifying sha256 digest":
                    console.print("Verificando integridade...")
                elif status == "success":
                    console.print(f"[green bold]✓[/] {model} baixado com sucesso.")

            yield chunk
    finally:
        if progress:
            progress.stop()


def create_progress_bar() -> Progress:
    """
    Create a progress bar for downloads.

    Returns:
        Rich Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def render_compare_header(model: str, index: int, total: int) -> None:
    """
    Display compare model header.

    Format: ── [N/TOTAL] {model} ────────────────────

    Args:
        model: Model name
        index: Current model index (1-based)
        total: Total number of models
    """
    console.print()
    console.print(f"[bold]── [{index}/{total}] {model}[/] {'─' * 40}")


def render_compare_table(
    results: list,
    quiet: bool = False,
    seed_provided: bool = False,
) -> None:
    """
    Display comparison table with highlights and warnings.

    Args:
        results: List of ModelResult objects
        quiet: If True, suppress output
        seed_provided: If True, don't show seed warning
    """
    if quiet:
        return

    table = Table(title="Comparação de Modelos", show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Tokens", justify="right")
    table.add_column("Tempo", justify="right")
    table.add_column("Velocidade", justify="right")

    valid_results = [r for r in results if r.error is None]

    if valid_results:
        max_tps = max(r.tokens_per_second for r in valid_results)
        min_tokens = min(r.eval_count for r in valid_results)
    else:
        max_tps = 0
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
            if result.tokens_per_second == max_tps and len(valid_results) > 1:
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

    console.print()
    console.print(table)

    if not seed_provided:
        console.print()
        console.print("[yellow]⚠ Sem --seed: resultados podem variar entre execuções.[/]")
        console.print("  Para comparação reproduzível: miru compare ... --seed 42")
