"""Renderer module for terminal output formatting using Rich."""

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from miru.core.i18n import t
from miru.latex_unicode import latex_to_unicode

if TYPE_CHECKING:
    pass

console = Console()
console_stderr = Console(stderr=True)


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable format (GB/MB/KB)."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def format_date(date_str: str) -> str:
    """Format ISO date string to local date."""
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
    """Consume chunks from Ollama client generator and display tokens progressively."""
    async for chunk in chunks:
        if not quiet:
            text = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
            if text:
                print(latex_to_unicode(text), end="", flush=True)

        yield chunk

        if chunk.get("done") and not quiet:
            render_metrics(chunk)


def render_metrics(chunk: dict, quiet: bool = False) -> None:
    """Display metrics line at end of generation."""
    if quiet:
        return

    metrics_str = format_metrics(chunk)
    if metrics_str:
        print(f"✓ {metrics_str}")


def format_metrics(chunk: dict) -> str:
    """Format metrics from generation chunk into a string."""
    eval_count = chunk.get("eval_count", 0)
    total_duration_ns = chunk.get("total_duration", 0)
    eval_duration_ns = chunk.get("eval_duration", 0)

    total_seconds = total_duration_ns / 1e9 if total_duration_ns else 0.0

    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
    elif total_duration_ns and total_duration_ns > 0:
        tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
    else:
        tokens_per_second = 0.0

    if tokens_per_second > 0:
        return (
            f"{eval_count} {t('renderer.tokens_metric')} · "
            f"{total_seconds:.1f}s · {tokens_per_second:.1f} {t('renderer.speed_metric')}"
        )
    return f"{eval_count} {t('renderer.tokens_metric')} · {total_seconds:.1f}s"


def render_error(message: str, hint: str | None = None) -> None:
    """Display error message in stderr."""
    console_stderr.print(f"[red bold]\u2717[/] {message}")
    if hint:
        console_stderr.print(f"  {hint}")


def render_warning(message: str) -> None:
    """Display warning message in stderr."""
    console_stderr.print(f"[yellow]\u26a0[/] {message}")


def render_markdown(text: str) -> None:
    """Render Markdown text with Rich formatting."""
    console.print(Markdown(text))


async def render_stream_as_markdown(
    chunks: AsyncIterator[dict],
    quiet: bool = False,
    show_metrics: bool = True,
) -> tuple[str, dict | None]:
    """Consume stream with animated dots, render formatted Markdown at end."""
    import asyncio
    import sys

    response_parts = []
    final_chunk = None

    if not quiet:

        async def show_progress():
            dots = [".", "..", "..."]
            idx = 0
            while True:
                sys.stdout.write(f"\r{t('renderer.generating')}{dots[idx]}")
                sys.stdout.flush()
                await asyncio.sleep(0.3)
                idx = (idx + 1) % 3

        progress_task = asyncio.create_task(show_progress())

        try:
            async for chunk in chunks:
                text = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
                if text:
                    response_parts.append(text)

                if chunk.get("done"):
                    final_chunk = chunk
        finally:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
    else:
        async for chunk in chunks:
            text = chunk.get("response", "") or chunk.get("message", {}).get("content", "")
            if text:
                response_parts.append(text)

            if chunk.get("done"):
                final_chunk = chunk

    full_response = "".join(response_parts)
    full_response = latex_to_unicode(full_response)

    if quiet:
        return full_response, final_chunk

    if response_parts:
        print()
        console.print(Markdown(full_response))

        if show_metrics and final_chunk:
            print()
            render_metrics(final_chunk)

    return full_response, final_chunk


def _render_models_table_internal(models: list[dict], quiet: bool = False) -> None:
    if not models:
        console.print(
            f"[yellow]{t('renderer.no_models')}[/] "
            f"Use: [bold]{t('renderer.no_models_hint')}[/]"
        )
        return

    if quiet:
        for model in models:
            print(model.get("name", ""))
        return

    table = Table(
        title=t("renderer.available_models"),
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column(t("renderer.model_column"), style="green")
    table.add_column(t("renderer.size_column"), justify="right")
    table.add_column(t("renderer.modified_column"), justify="center")

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
    console.print(f"\n{t('renderer.models_count', count=len(models))}")


def render_model_table(models: list[dict], quiet: bool = False) -> None:
    """Display Rich table with available models."""
    _render_models_table_internal(models, quiet)


def render_models_table(models: list[dict], quiet: bool = False) -> None:
    """Display Rich table with available models."""
    _render_models_table_internal(models, quiet)


def render_empty_models() -> None:
    """Display empty models list message."""
    console.print(
        f"[yellow]{t('renderer.no_models')}[/] "
        f"Use: [bold]{t('renderer.no_models_hint')}[/]"
    )


def render_model_info(
    model_name: str,
    data: dict,
    capabilities: dict,
    quiet: bool = False,
) -> None:
    """Display model information as Rich panel."""
    if quiet:
        print(f"{model_name}")
        return

    details = data.get("details", {})
    families = details.get("families", [])
    parameter_size = details.get("parameter_size", "unknown")
    quantization = details.get("quantization_level", "unknown")

    content_lines = []

    content_lines.append(f"[bold]{t('renderer.identification')}[/]")
    content_lines.append(
        f"  {t('renderer.families')}      {', '.join(families) if families else '-'}"
    )
    content_lines.append(f"  {t('renderer.parameters')}      {parameter_size}")
    content_lines.append(f"  {t('renderer.quantization')}     {quantization}")
    content_lines.append("")

    content_lines.append(f"[bold]{t('renderer.capabilities')}[/]")

    supports_vision = capabilities.get("supports_vision", False)
    vision_emoji = "\U0001f5bc" if supports_vision else "\u25cb"
    vision_text = t("renderer.yes") if supports_vision else t("renderer.no")
    content_lines.append(f"  {vision_emoji} {t('renderer.vision')}                {vision_text}")

    capabilities_list = capabilities.get("capabilities", [])

    if capabilities_list:
        if supports_vision and "vision" in capabilities_list:
            capabilities_list = [c for c in capabilities_list if c != "vision"]

        importance_order = [
            "tools",
            "thinking",
            "audio",
            "completion",
        ]

        capability_names = {
            "tools": "Tools/Function Calling",
            "thinking": "Thinking",
            "audio": "\u00c1udio",
            "completion": "Completion",
        }

        sorted_capabilities = sorted(
            capabilities_list,
            key=lambda x: (
                importance_order.index(x) if x in importance_order else len(importance_order)
            ),
        )

        for cap in sorted_capabilities:
            cap_name = capability_names.get(cap, cap.capitalize())
            content_lines.append(f"  \u2713 {cap_name}")

    max_context = capabilities.get("max_context", 2048)
    content_lines.append(f"  \U0001f4d0 {t('renderer.max_context')}     {max_context:,} tokens")
    content_lines.append("")

    parameters_str = data.get("parameters", "")
    if parameters_str:
        params = _parse_parameters(parameters_str)
        if params:
            content_lines.append(f"[bold]{t('renderer.default_params')}[/]")
            for key, value in params.items():
                content_lines.append(f"  {key}    {value}")

    content = "\n".join(content_lines)
    panel = Panel(content, title=model_name, border_style="cyan")
    console.print(panel)


def _parse_parameters(params_str: str) -> dict[str, str]:
    """Parse parameters string into dict."""
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
    """Consume pull chunks and display visual progress. Re-yields each chunk."""
    progress: Progress | None = None
    task_id: TaskID | None = None

    try:
        async for chunk in chunks:
            status = chunk.get("status", "")

            if quiet:
                if status == "success":
                    print(f"\u2713 {t('renderer.download_complete')}")
            else:
                if status == "pulling manifest":
                    console.print(t("renderer.pulling_manifest"))
                elif status == "downloading":
                    if progress is None:
                        progress = create_progress_bar()
                        progress.start()
                        task_id = progress.add_task(
                            t("renderer.downloading"), total=None
                        )

                    completed = chunk.get("completed", 0)
                    total = chunk.get("total", 0)

                    if total and total > 0:
                        if task_id is not None:
                            progress.update(task_id, completed=completed, total=total)
                    else:
                        if task_id is not None:
                            progress.update(task_id, completed=completed)

                elif status == "verifying sha256 digest":
                    console.print(t("renderer.verifying"))
                elif status == "success":
                    console.print(
                        f"[green bold]\u2713[/] "
                        f"{t('renderer.downloaded_success', model=model)}"
                    )

            yield chunk
    finally:
        if progress:
            progress.stop()


def create_progress_bar() -> Progress:
    """Create a progress bar for downloads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def render_compare_header(model: str, index: int, total: int) -> None:
    """Display compare model header."""
    hline = "\u2500" * 40
    console.print()
    console.print(f"[bold]\u2500\u2500 [{index}/{total}] {model}[/] {hline}")


def render_compare_table(
    results: list,
    quiet: bool = False,
    seed_provided: bool = False,
) -> None:
    """Display comparison table with highlights and warnings."""
    if quiet:
        return

    table = Table(
        title=t("renderer.compare_title"),
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column(t("renderer.compare_model_column"), style="green")
    table.add_column(t("renderer.compare_tokens_column"), justify="right")
    table.add_column(t("renderer.compare_time_column"), justify="right")
    table.add_column(t("renderer.compare_speed_column"), justify="right")

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
                "\u2014 \u2717",
                "\u2014",
                "\u2014",
                style="red dim",
            )
        else:
            tokens_str = f"{result.eval_count}"
            if result.eval_count == min_tokens and len(valid_results) > 1:
                tokens_str = f"{result.eval_count} \u2713"

            tempo_str = f"{result.total_duration_ns / 1e9:.1f}s"

            speed_str = (
                f"{result.tokens_per_second:.1f} {t('renderer.speed_metric')}"
            )
            if result.tokens_per_second == max_tps and len(valid_results) > 1:
                speed_str += " \u2713"
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
        console.print(f"[yellow]\u26a0 {t('renderer.compare_no_seed_warning')}[/]")
        console.print(f"  {t('renderer.compare_no_seed_hint')}")
