"""Rendering utilities for terminal output.

Provides consistent output formatting with i18n support.
"""

from typing import Any

from rich.console import Console
from rich.syntax import Syntax
from rich.syntax import Syntax as RichSyntax
from rich.table import Table

from miru.core.i18n import t

console = Console()


def render_error(message: str, suggestion: str | None = None) -> None:
    """Render error message with i18n support.
    
    Args:
        message: Error message (already translated or raw)
        suggestion: Optional suggestion text
        
    Example:
        >>> render_error(t("error.model_not_found", model="gemma3"))
        ✗ Modelo 'gemma3' não encontrado.
        
        Para baixar: miru pull gemma3
    """
    console.print(f"[red bold]✗[/] {message}")
    if suggestion:
        console.print(f"[dim]{suggestion}[/]")


def render_success(message: str) -> None:
    """Render success message.
    
    Args:
        message: Success message
        
    Example:
        >>> render_success(t("success.model_pulled", model="gemma3"))
        ✓ Modelo 'gemma3' baixado com sucesso.
    """
    console.print(f"[green bold]✓[/] {message}")


def render_warning(message: str) -> None:
    """Render warning message.
    
    Args:
        message: Warning message
        
    Example:
        >>> render_warning("This action cannot be undone")
        ⚠ This action cannot be undone
    """
    console.print(f"[yellow bold]⚠[/] {message}")


def render_info(message: str) -> None:
    """Render info message.
    
    Args:
        message: Info message
        
    Example:
        >>> render_info("Processing file...")
        ℹ Processing file...
    """
    console.print(f"[blue]ℹ[/] {message}")


def render_model_table(
    models: list[dict[str, Any]],
    title: str | None = None,
) -> None:
    """Render models as a table.
    
    Args:
        models: List of model dicts from API
        title: Optional table title
        
    Example:
        >>> render_model_table([{"name": "gemma3:latest", "size": 4993668096}])
    """
    if not models:
        console.print(f"[dim]{t('models.empty')}[/]")
        return
    
    table = Table(title=title)
    
    table.add_column("Name", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Modified", style="dim")
    
    for model in models:
        name = model.get("name", "unknown")
        size_bytes = model.get("size", 0)
        
        if size_bytes >= 1_073_741_824:
            size = f"{size_bytes / 1_073_741_824:.1f} GB"
        elif size_bytes >= 1_048_576:
            size = f"{size_bytes / 1_048_576:.0f} MB"
        else:
            size = f"{size_bytes / 1024:.1f} KB"
        
        modified = model.get("modified_at", "")
        if modified and "T" in modified:
            modified = modified.split("T")[0]
        
        table.add_row(name, size, modified)
    
    console.print(table)


def render_metrics(chunk: dict[str, Any], prefix: str = "") -> None:
    """Render generation metrics.
    
    Args:
        chunk: Final chunk from API with metrics
        prefix: Optional prefix for output
        
    Example:
        >>> render_metrics({"eval_count": 100, "eval_duration": 2000000000})
        100 tokens · 50.0 tok/s · 2.0s
    """
    eval_count = chunk.get("eval_count", 0)
    eval_duration_ns = chunk.get("eval_duration", 0)
    total_duration_ns = chunk.get("total_duration", 0)
    
    if eval_count == 0:
        return
    
    duration_ns = eval_duration_ns if eval_duration_ns > 0 else total_duration_ns
    duration_seconds = duration_ns / 1e9
    
    if duration_seconds > 0:
        speed = eval_count / duration_seconds
        console.print(
            f"{prefix}[dim]{eval_count} tokens · {speed:.1f} tok/s · {duration_seconds:.1f}s[/]"
        )
    else:
        console.print(f"{prefix}[dim]{eval_count} tokens[/]")


def render_code(code: str, language: str = "python", line_numbers: bool = False) -> None:
    """Render code with syntax highlighting.
    
    Args:
        code: Code string
        language: Programming language
        line_numbers: Whether to show line numbers
    """
    syntax = Syntax(code, language, line_numbers=line_numbers, theme="monokai")
    console.print(syntax)


def render_markdown(text: str) -> None:
    """Render markdown text.
    
    Args:
        text: Markdown text
        
    Note:
        Delegates to output.renderer for consistency.
    """
    from miru.output.renderer import render_markdown as _render
    
    _render(text)


def render_table(
    headers: list[str],
    rows: list[list[str]],
    title: str | None = None,
) -> None:
    """Render a simple table.
    
    Args:
        headers: Column headers
        rows: Table rows
        title: Optional table title
    """
    table = Table(title=title)
    
    for header in headers:
        table.add_column(header, style="cyan")
    
    for row in rows:
        table.add_row(*row)
    
    console.print(table)