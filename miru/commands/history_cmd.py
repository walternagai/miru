"""History command for managing prompt history."""

import json
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.history import clear_history, get_history, search_history

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
        console.print("[green bold]✓[/] History cleared")
        return

    if search:
        entries = search_history(search, limit=limit)
    else:
        entries = get_history(limit=limit, command=command)

    if not entries:
        console.print("[dim]Nenhum histórico encontrado[/]")
        return

    if format == "json":
        output = [e.to_dict() for e in entries]
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    table = Table(title="Histórico de Prompts", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Data/Hora", width=16)
    table.add_column("Comando", width=8)
    table.add_column("Modelo", style="green", width=20)
    table.add_column("Prompt", width=40)
    table.add_column("Status", width=8)

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
        console.print(f"[dim]Use: miru history show <index> para ver detalhes[/]")


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
        console.print(f"[red bold]✗[/] Entry {index} not found")
        sys.exit(1)

    console.print(f"[bold]Data/Hora:[/] {entry.timestamp}")
    console.print(f"[bold]Comando:[/] {entry.command}")
    console.print(f"[bold]Modelo:[/] {entry.model}")
    console.print(f"[bold]Status:[/] {'✓ Success' if entry.success else '✗ Failed'}")

    if entry.system_prompt:
        console.print(f"[bold]System Prompt:[/]")
        console.print(
            f"  {entry.system_prompt[:100]}{'...' if len(entry.system_prompt) > 100 else ''}"
        )

    console.print()
    console.print("[bold]Prompt:[/]")
    console.print(entry.prompt)

    if entry.response:
        console.print()
        console.print("[bold]Response:[/]")
        console.print(entry.response)

    if entry.metrics:
        console.print()
        console.print("[bold]Métricas:[/]")
        metrics = entry.metrics
        if "eval_count" in metrics:
            console.print(f"  Tokens: {metrics['eval_count']}")
        if "tokens_per_second" in metrics:
            console.print(f"  Velocidade: {metrics['tokens_per_second']:.1f} tok/s")
        if "total_duration_ns" in metrics:
            total_seconds = metrics["total_duration_ns"] / 1e9
            console.print(f"  Tempo: {total_seconds:.1f}s")

    if entry.error:
        console.print()
        console.print(f"[bold]Erro:[/] {entry.error}")
