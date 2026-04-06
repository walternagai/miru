"""Renderer module for backward compatibility - delegates to output module."""

# Re-export all functions from output module for backward compatibility
# Additional functions from old renderer not in output module
from typing import Any

from rich.console import Console
from rich.text import Text

from miru.output import (  # type: ignore
    console,
    create_progress_bar,
    format_date,
    format_size,
    models_to_json,
    print_json,
    render_compare_header,
    render_compare_table,
    render_empty_models,
    render_error,
    render_metrics,
    render_model_info,
    render_model_table,
    render_models_table,
    render_pull_progress,
    render_warning,
    result_to_json,
    stream_tokens,
    to_json,
)

_console = Console()


def render_success(message: str) -> None:
    """Render success message."""
    _console.print(f"[green bold]✓[/] {message}")


def create_spinner(message: str) -> Any:
    """
    Create a spinner status.

    Args:
        message: Status message

    Returns:
        Rich Live instance
    """
    from rich.live import Live

    text = Text(message, style="yellow")
    return Live(text, console=_console)


def render_models_json(models: list[dict[str, Any]], quiet: bool = False) -> None:
    """
    Render models list as JSON.

    Args:
        models: List of model dicts from /api/tags
        quiet: If True, output compact JSON
    """
    import json

    from miru.output.formatter import models_to_json

    output = models_to_json(models)

    if quiet:
        print(json.dumps(output, separators=(",", ":")))
    else:
        print(json.dumps(output, indent=2))


def render_model_info_json(
    data: dict[str, Any],
    capabilities: dict[str, Any],
    quiet: bool = False
) -> None:
    """
    Render model information as JSON.

    Args:
        data: Full model data from /api/show
        capabilities: Capabilities dict from get_capabilities
        quiet: If True, output compact JSON
    """
    import json

    output = {
        **data,
        "capabilities": capabilities,
    }

    if quiet:
        print(json.dumps(output, separators=(",", ":")))
    else:
        print(json.dumps(output, indent=2))


__all__ = [
    # From output module
    "console",
    "create_progress_bar",
    "format_date",
    "format_size",
    "models_to_json",
    "print_json",
    "render_compare_header",
    "render_compare_table",
    "render_empty_models",
    "render_error",
    "render_metrics",
    "render_model_info",
    "render_model_table",
    "render_models_table",
    "render_pull_progress",
    "render_warning",
    "result_to_json",
    "stream_tokens",
    "to_json",
    # Additional exports
    "create_spinner",
    "render_success",
    "render_models_json",
    "render_model_info_json",
]
