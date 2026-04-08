"""Session save and restore functionality."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from miru.config_manager import CONFIG_DIR, ensure_config_dir

console = Console()
SESSIONS_DIR = CONFIG_DIR / "sessions"
FAVORITES_FILE = CONFIG_DIR / "favorites.json"


def ensure_sessions_dir() -> None:
    """Ensure sessions directory exists."""
    ensure_config_dir()
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_favorites() -> set[str]:
    """Load favorite session names."""
    if not FAVORITES_FILE.exists():
        return set()
    try:
        with open(FAVORITES_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_favorites(favorites: set[str]) -> None:
    """Save favorite session names."""
    ensure_config_dir()
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(list(favorites), f)


def toggle_favorite(name: str) -> bool:
    """Toggle session favorite status. Returns new status."""
    favorites = load_favorites()
    if name in favorites:
        favorites.discard(name)
        is_favorite = False
    else:
        favorites.add(name)
        is_favorite = True
    save_favorites(favorites)
    return is_favorite


def is_favorite(name: str) -> bool:
    """Check if session is favorite."""
    return name in load_favorites()


def get_session_path(name: str) -> Path:
    """Get session file path."""
    return SESSIONS_DIR / f"{name}.json"


def list_sessions() -> list[dict[str, Any]]:
    """List all saved sessions."""
    ensure_sessions_dir()

    sessions: list[dict[str, Any]] = []

    if not SESSIONS_DIR.exists():
        return sessions

    for file in SESSIONS_DIR.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                sessions.append(
                    {
                        "name": file.stem,
                        "model": data.get("model", "unknown"),
                        "turns": len(data.get("messages", [])) // 2,
                        "created": data.get("created", ""),
                        "updated": data.get("updated", ""),
                    }
                )
        except Exception:
            continue

    sessions.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return sessions


def save_session(
    name: str, model: str, messages: list[dict[str, Any]], system_prompt: str | None = None
) -> None:
    """Save session to file."""
    ensure_sessions_dir()

    session_data: dict[str, Any] = {
        "name": name,
        "model": model,
        "system_prompt": system_prompt,
        "messages": messages,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "version": 1,
    }

    path = get_session_path(name)

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
                session_data["created"] = existing.get("created", session_data["created"])
        except Exception:
            pass

    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)


def load_session(name: str) -> dict[str, Any] | None:
    """Load session from file."""
    path = get_session_path(name)

    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    except Exception:
        return None


def delete_session(name: str) -> bool:
    """Delete a session."""
    path = get_session_path(name)

    if not path.exists():
        return False

    path.unlink()
    return True


def export_session(name: str, output: str | None = None, format: str = "json") -> None:
    """Export session to different formats."""
    session = load_session(name)

    if not session:
        console.print(f"[red bold]✗[/] Session '{name}' not found")
        sys.exit(1)

    if output is None:
        output = f"{name}.{format if format != 'markdown' else 'md'}"

    if format == "json":
        with open(output, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        console.print(f"[green bold]✓[/] Session exported to {output}")
        return

    if format == "markdown" or format == "md":
        lines = [
            f"# Chat Session: {session['name']}",
            "",
            f"**Model:** {session['model']}",
            f"**Created:** {session.get('created', 'unknown')}",
            f"**Turns:** {len(session.get('messages', [])) // 2}",
            "",
        ]

        if session.get("system_prompt"):
            lines.append("## System Prompt")
            lines.append(f"```\n{session['system_prompt']}\n```\n")

        for msg in session.get("messages", []):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                continue
            elif role == "user":
                lines.append("## User")
            elif role == "assistant":
                lines.append("## Assistant")
            else:
                lines.append(f"## {role.title()}")

            lines.append(f"{content}\n")

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        console.print(f"[green bold]✓[/] Session exported to {output}")
        return

    if format == "txt":
        lines = []

        for msg in session.get("messages", []):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                lines.append(f"[SYSTEM]\n{content}\n")
            elif role == "user":
                lines.append(f"[USER]\n{content}\n")
            elif role == "assistant":
                lines.append(f"[ASSISTANT]\n{content}\n")
            else:
                lines.append(f"[{role.upper()}]\n{content}\n")

        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        console.print(f"[green bold]✓[/] Session exported to {output}")
        return

    console.print(f"[red bold]✗[/] Unsupported format: {format}")
    console.print("[dim]Supported formats: json, markdown, txt")
    sys.exit(1)


def session_list() -> None:
    """List all saved sessions."""
    sessions = list_sessions()

    if not sessions:
        console.print("[dim]No saved sessions[/]")
        console.print("[dim]Use 'miru chat --session <name>' to create a session[/]")
        return

    table = Table(title="Saved Sessions", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Model")
    table.add_column("Turns", justify="right")
    table.add_column("Updated")

    for session in sessions:
        updated = session.get("updated", "")[:16] if session.get("updated") else "—"
        table.add_row(
            session.get("name", "unknown"),
            session.get("model", "unknown"),
            str(session.get("turns", 0)),
            updated,
        )

    console.print(table)


def session_show(name: str) -> None:
    """Show session details."""
    session = load_session(name)

    if not session:
        console.print(f"[red bold]✗[/] Session '{name}' not found")
        sys.exit(1)

    console.print(f"[bold]Name:[/] {session.get('name')}")
    console.print(f"[bold]Model:[/] {session.get('model')}")
    console.print(f"[bold]Created:[/] {session.get('created', 'unknown')[:19]}")
    console.print(f"[bold]Updated:[/] {session.get('updated', 'unknown')[:19]}")

    if session.get("system_prompt"):
        console.print("[bold]System Prompt:[/]")
        console.print(f"  {session['system_prompt'][:100]}...")

    console.print(f"[bold]Messages:[/] {len(session.get('messages', []))}")


app = typer.Typer(help="Manage chat sessions")


@app.command("list")
def session_list_cmd() -> None:
    """List all saved sessions.

    Example:
        miru session list
    """
    session_list()


@app.command("show")
def session_show_cmd(
    name: Annotated[str, typer.Argument(help="Session name")],
) -> None:
    """Show session details.

    Example:
        miru session show my-session
    """
    session_show(name)


@app.command("delete")
def session_delete_cmd(
    name: Annotated[str, typer.Argument(help="Session name")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a session.

    Example:
        miru session delete my-session
    """
    if not force:
        console.print(f"[yellow]Delete session '{name}'?[/] Use --force to confirm")
        return

    if delete_session(name):
        console.print(f"[green bold]✓[/] Session '{name}' deleted")
    else:
        console.print(f"[red bold]✗[/] Session '{name}' not found")
        sys.exit(1)


@app.command("export")
def session_export_cmd(
    name: Annotated[str, typer.Argument(help="Session name")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file")] = None,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Format (json/markdown/txt)")
    ] = "json",
) -> None:
    """Export a session.

    Examples:
        miru session export my-session --output session.json
        miru session export my-session --output session.md --format markdown
        miru session export my-session --output session.txt --format txt
    """
    if output is None:
        output = f"{name}.{format if format != 'markdown' else 'md'}"

    export_session(name, output, format)


@app.command("rename")
def session_rename_cmd(
    old_name: Annotated[str, typer.Argument(help="Current session name")],
    new_name: Annotated[str, typer.Argument(help="New session name")],
) -> None:
    """Rename a session.

    Example:
        miru session rename old-name new-name
    """
    session = load_session(old_name)

    if not session:
        console.print(f"[red bold]✗[/] Session '{old_name}' not found")
        sys.exit(1)

    if get_session_path(new_name).exists():
        console.print(f"[red bold]✗[/] Session '{new_name}' already exists")
        sys.exit(1)

    session["name"] = new_name

    with open(get_session_path(new_name), "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

    get_session_path(old_name).unlink()

    console.print(f"[green bold]✓[/] Session renamed to '{new_name}'")
