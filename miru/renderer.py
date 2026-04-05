"""Renderer module for terminal output formatting."""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

console = Console()


def format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable format (GB/MB/KB).

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "5.0 GB", "256 MB")
    """
    if size_bytes >= 1_073_741_824:  # 1 GB
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:  # 1 MB
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1024:  # 1 KB
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
        # Try to extract date part from ISO format
        if "T" in date_str:
            return date_str.split("T")[0]
        return date_str[:10]
    except (ValueError, IndexError):
        return date_str


def render_models_table(models: list[dict[str, Any]], quiet: bool = False) -> None:
    """
    Render models list as table (text mode) or JSON.

    Args:
        models: List of model dicts from /api/tags
        quiet: If True, output minimal format
    """
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


def render_models_json(models: list[dict[str, Any]], quiet: bool = False) -> None:
    """
    Render models list as JSON.

    Args:
        models: List of model dicts from /api/tags
        quiet: If True, output compact JSON
    """
    output = []
    for model in models:
        output.append({
            **model,
            "size_human": format_size(model.get("size", 0)),
        })

    if quiet:
        print(json.dumps(output, separators=(",", ":")))
    else:
        print(json.dumps(output, indent=2))


def render_empty_models() -> None:
    """Render empty models list message."""
    console.print("[yellow]Nenhum modelo instalado.[/] Use: [bold]miru pull <model>[/]")


def render_error(message: str, suggestion: str | None = None) -> None:
    """
    Render error message with optional suggestion.

    Args:
        message: Error message
        suggestion: Optional action to take
    """
    console.print(f"[red bold]✗[/] {message}")
    if suggestion:
        console.print(f"  {suggestion}")


def render_success(message: str) -> None:
    """Render success message."""
    console.print(f"[green bold]✓[/] {message}")


def render_model_info(
    model_name: str,
    data: dict[str, Any],
    capabilities: dict[str, Any],
    quiet: bool = False,
) -> None:
    """
    Render model information as panel (text mode) or JSON.

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

    # Build content lines
    content_lines = []

    # Identification section
    content_lines.append("[bold]Identificação[/]")
    content_lines.append(f"  Família(s)      {', '.join(families) if families else '-'}")
    content_lines.append(f"  Parâmetros      {parameter_size}")
    content_lines.append(f"  Quantização     {quantization}")
    content_lines.append("")

    # Capabilities section
    content_lines.append("[bold]Capacidades[/]")
    supports_vision = capabilities.get("supports_vision", False)
    vision_emoji = "🖼" if supports_vision else "○"
    vision_text = "sim" if supports_vision else "não"
    content_lines.append(f"  {vision_emoji} Suporte a imagens   {vision_text}")

    max_context = capabilities.get("max_context", 2048)
    content_lines.append(f"  📐 Contexto máximo     {max_context:,} tokens")
    content_lines.append("")

    # Parameters section
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


def render_model_info_json(data: dict[str, Any], capabilities: dict[str, Any], quiet: bool = False) -> None:
    """
    Render model information as JSON.

    Args:
        data: Full model data from /api/show
        capabilities: Capabilities dict from get_capabilities
        quiet: If True, output compact JSON
    """
    output = {
        **data,
        "capabilities": capabilities,
    }

    if quiet:
        print(json.dumps(output, separators=(",", ":")))
    else:
        print(json.dumps(output, indent=2))


def _parse_parameters(params_str: str) -> dict[str, str]:
    """
    Parse parameters string into dict.

    Args:
        params_str: Parameters string (e.g., "num_ctx\t4096\nnum_batch\t512")

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


def create_spinner(message: str) -> Any:
    """
    Create a spinner status.

    Args:
        message: Status message

    Returns:
        Rich Live instance
    """
    from rich.live import Live
    from rich.text import Text

    text = Text(message, style="yellow")
    return Live(text, console=console)


def render_pull_progress(
    model: str,
    chunks: Any,
    quiet: bool = False,
) -> None:
    """
    Render pull progress with progress bar or spinner.

    Args:
        model: Model name
        chunks: Async iterator of progress chunks
        quiet: If True, output minimal format
    """