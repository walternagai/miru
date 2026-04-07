"""UI module - rendering and user interaction.

Separates all UI concerns (console output, progress, prompts)
from business logic.
"""

from miru.ui.progress import (
    ProgressReporter,
    create_progress,
    create_spinner,
    track_progress,
)
from miru.ui.prompts import (
    confirm,
    prompt_choice,
    prompt_input,
)
from miru.ui.render import (
    render_error,
    render_success,
    render_warning,
    render_info,
    render_model_table,
    render_metrics,
)

__all__ = [
    "ProgressReporter",
    "create_progress",
    "create_spinner",
    "track_progress",
    "confirm",
    "prompt_choice",
    "prompt_input",
    "render_error",
    "render_success",
    "render_warning",
    "render_info",
    "render_model_table",
    "render_metrics",
]