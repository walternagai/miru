"""Output rendering and formatting modules."""

from miru.output.formatter import (
    models_to_json,
    print_json,
    print_plain,
    result_to_json,
    to_json,
)
from miru.output.renderer import (
    console,
    create_progress_bar,
    format_date,
    format_size,
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
    stream_tokens,
)
from miru.output.streaming import (
    collect_stream,
    render_json_output,
    render_stream,
)
from miru.output.streaming import (
    render_metrics as streaming_render_metrics,
)

__all__ = [
    # Formatter
    "models_to_json",
    "print_json",
    "print_plain",
    "result_to_json",
    "to_json",
    # Renderer
    "console",
    "create_progress_bar",
    "format_date",
    "format_size",
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
    "stream_tokens",
    # Streaming (backward compatible)
    "collect_stream",
    "render_json_output",
    "render_stream",
    "streaming_render_metrics",
]
