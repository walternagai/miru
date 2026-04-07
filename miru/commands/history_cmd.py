"""History command for managing prompt history."""

import json
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.history import clear_history, get_history, search_history
from miru.core.i18n import t

console = Console()


def history_cmd(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of entries to show")] = 20,
    command: Annotated[
        str | None, typer.Option("--command", "-c", help="Filter by command type")
    ] = None,
    search: Annotated[str | None, typer.Option("--search", "-s", help="Search query")] = None,
    clear: Annotated[bool, typer.Option("--clear", help="Clear all history")] = False,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (text/json)")
    ] = "text",
) -> None:
    """View and manage prompt history.

    Examples:
        miru history
        miru history --limit 50
        miru history --command run
        miru history --search "python"
        miru history --clear
    """
    if clear:
        clear_history()
        console.print(f"[green bold]✓[/] {t('history.cleared')}")
        return

    if search:
        entries = search_history(search, limit=limit)
    else:
        entries = get_history(limit=limit, command=command)

    if not entries:
        console.print(f"[dim]{t('history.none_found')}[/]")
        return

    if format == "json":
        output = [e.to_dict() for e in entries]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    table = Table(title=t("history.title"), show_header=True, header_style="bold cyan")
    table.add_column(t("history.index_header"), style="dim", width=4)
    table.add_column(t("history.datetime_header"), width=16)
    table.add_column(t("history.command_header"), width=8)
    table.add_column(t("history.model_header"), style="green", width=20)
    table.add_column(t("history.prompt_header"), width=40)
    table.add_column(t("history.status_header"), width=8)

    for idx, entry in enumerate(entries):
        timestamp = entry.timestamp[:16] if len(entry.timestamp) >= 16 else entry.timestamp
        cmd = entry.command
        model = entry.model[:18] + "..." if len(entry.model) > 20 else entry.model
        prompt = entry.prompt[:37] + "..." if len(entry.prompt) > 40 else entry.prompt
        status = "[green]✓[/]" if entry.success else "[red]✗[/]"

        table.add_row(str(idx), timestamp, cmd, model, prompt, status)

    console.print(table)

    if entries:
        console.print()
        console.print(f"[dim]{t('history.use_show')}[/]")


def history_show(
    index: Annotated[int, typer.Argument(help="History entry index")] = 0,
) -> None:
    """Show detailed history entry.

    Example:
        miru history show 0
    """
    from miru.history import get_history_by_index

    entry = get_history_by_index(index)

    if not entry:
        console.print(f"[red bold]✗[/] {t('history.entry_not_found', index=index)}")
        sys.exit(1)

    console.print(f"[bold]{t('history.datetime_label')}[/] {entry.timestamp}")
    console.print(f"[bold]{t('history.command_label')}[/] {entry.command}")
    console.print(f"[bold]{t('history.model_label')}[/] {entry.model}")
    console.print(f"[bold]{t('history.status_label')}[/] {'✓ ' + t('history.success') if entry.success else '✗ ' + t('history.failed')}")

    if entry.system_prompt:
        console.print(f"[bold]{t('history.system_prompt_label')}[/]")
        console.print(
            f"  {entry.system_prompt[:100]}{'...' if len(entry.system_prompt) > 100 else ''}"
        )

    console.print()
    console.print(f"[bold]{t('history.prompt_label')}[/]")
    console.print(entry.prompt)

    if entry.response:
        console.print()
        console.print(f"[bold]{t('history.response_label')}[/]")
        console.print(entry.response)

    if entry.metrics:
        console.print()
        console.print(f"[bold]{t('history.metrics_label')}[/]")
        metrics = entry.metrics
        if "eval_count" in metrics:
            console.print(f"  {t('history.tokens')} {metrics['eval_count']}")
        if "tokens_per_second" in metrics:
            console.print(f"  {t('history.speed', speed=metrics['tokens_per_second'])}")
        if "total_duration_ns" in metrics:
            total_seconds = metrics["total_duration_ns"] / 1e9
            console.print(f"  {t('history.time', time=total_seconds)}")

    if entry.error:
        console.print()
        console.print(f"[bold]{t('history.error_label')}[/] {entry.error}")