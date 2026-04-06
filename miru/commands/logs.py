"""Logs command for viewing execution logs."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.config_manager import LOG_DIR, ensure_config_dir

console = Console()


def get_log_files() -> list[Path]:
    """Get all log files sorted by date (newest first)."""
    ensure_config_dir()

    if not LOG_DIR.exists():
        return []

    files = sorted(LOG_DIR.glob("miru_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    return files


def logs(
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow log output")] = False,
    lines: Annotated[int, typer.Option("--lines", "-n", help="Number of lines to show")] = 50,
    latest: Annotated[bool, typer.Option("--latest", "-l", help="Show only latest log")] = False,
    list_files: Annotated[bool, typer.Option("--list", help="List log files")] = False,
) -> None:
    """View miru execution logs.

    Examples:
        miru logs
        miru logs --lines 100
        miru logs --follow
        miru logs --latest
        miru logs --list
    """
    if list_files:
        files = get_log_files()

        if not files:
            console.print("[dim]Nenhum log encontrado[/]")
            return

        table = Table(title="Log Files", show_header=True, header_style="bold cyan")
        table.add_column("Arquivo", style="green")
        table.add_column("Tamanho", justify="right")
        table.add_column("Modificado")

        for f in files:
            size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(f.name, f"{size:,} B", mtime)

        console.print(table)
        return

    files = get_log_files()

    if not files:
        console.print("[dim]Nenhum log encontrado[/]")
        return

    if latest:
        files = files[:1]

    import time

    for i, log_file in enumerate(files):
        if i > 0:
            console.print()

        console.print(f"[bold]{log_file.name}[/]")

        try:
            with open(log_file, encoding="utf-8") as f:
                log_lines = f.readlines()

            for line in log_lines[-lines:]:
                line = line.strip()
                if not line:
                    continue

                try:
                    import json

                    entry = json.loads(line)
                    level = entry.get("level", "INFO")
                    message = entry.get("message", "")
                    timestamp = entry.get("timestamp", "")[:19]

                    level_style = {
                        "DEBUG": "dim",
                        "INFO": "blue",
                        "WARNING": "yellow",
                        "ERROR": "red",
                    }.get(level, "white")

                    console.print(
                        f"[dim]{timestamp}[/] [{level_style}]{level:<8}[/{level_style}] {message}"
                    )
                except json.JSONDecodeError:
                    console.print(line)
        except Exception as e:
            console.print(f"[red]Error reading {log_file}: {e}[/]")

        if follow and i == 0:
            import json

            console.print("[dim]Following... (Ctrl+C to stop)[/]")
            with open(log_file, encoding="utf-8") as f:
                f.seek(0, 2)

                try:
                    while True:
                        line = f.readline()
                        if line:
                            try:
                                entry = json.loads(line.strip())
                                level = entry.get("level", "INFO")
                                message = entry.get("message", "")
                                timestamp = entry.get("timestamp", "")[:19]

                                level_style = {
                                    "DEBUG": "dim",
                                    "INFO": "blue",
                                    "WARNING": "yellow",
                                    "ERROR": "red",
                                }.get(level, "white")

                                console.print(
                                    f"[dim]{timestamp}[/] [{level_style}]{level:<8}[/{level_style}] {message}"
                                )
                            except json.JSONDecodeError:
                                continue
                        else:
                            time.sleep(0.1)
                except KeyboardInterrupt:
                    console.print("\n[dim]Stopped[/]")
                    break


def clear_logs(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Clear all logs.

    Example:
        miru logs-clear --force
    """
    if not force:
        console.print("[yellow]Deletar todos os logs?[/] Use --force para confirmar")
        return

    files = get_log_files()

    if not files:
        console.print("[dim]Nenhum log para deletar[/]")
        return

    for f in files:
        f.unlink()

    console.print(f"[green bold]✓[/] {len(files)} log(s) deletados")
