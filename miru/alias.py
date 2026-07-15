"""Alias management for model shortcuts."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
except ImportError:
    tomli_w = None

from miru.config_manager import ALIAS_FILE, ensure_config_dir

console = Console()


def _load_aliases() -> dict[str, str]:
    """Load aliases from file."""
    ensure_config_dir()

    if not ALIAS_FILE.exists():
        return {}

    try:
        with open(ALIAS_FILE, "rb") as f:
            data = tomllib.load(f)
            return data.get("aliases", {})
    except Exception:
        return {}


def _save_aliases(aliases: dict[str, str]) -> None:
    """Save aliases to file."""
    if tomli_w is None:
        console.print("[yellow]Warning: tomli_w not installed. Cannot save aliases.[/]")
        return

    ensure_config_dir()

    with open(ALIAS_FILE, "wb") as f:
        tomli_w.dump({"aliases": aliases}, f)


def resolve_alias(name: str) -> str:
    """Resolve an alias to the full model name.

    Args:
        name: Model name or alias

    Returns:
        Full model name (or original if not an alias)
    """
    aliases = _load_aliases()
    return aliases.get(name, name)


def alias_add(
    name: Annotated[str, typer.Argument(help="Alias name (e.g., 'g3')")],
    model: Annotated[str, typer.Argument(help="Full model name (e.g., 'gemma3:latest')")],
) -> None:
    """Add a model alias.

    Examples:
        miru alias add g3 gemma3:latest
        miru alias add qwen qwen2.5:7b
    """
    aliases = _load_aliases()

    if name in aliases and aliases[name] != model:
        console.print(f"[yellow]⚠ Alias '{name}' already exists: {aliases[name]}[/]")
        console.print(f"[dim]Use 'miru alias delete {name}' to remove it first[/]")
        return

    aliases[name] = model
    _save_aliases(aliases)

    console.print(f"[green bold]✓[/] Alias '{name}' -> '{model}' criado")
    console.print(f'[dim]Use: miru run {name} "prompt"[/]')


def alias_list() -> None:
    """List all aliases.

    Example:
        miru alias list
    """
    aliases = _load_aliases()

    if not aliases:
        console.print("[dim]Nenhum alias configurado[/]")
        console.print("[dim]Crie um: miru alias add <name> <model>[/]")
        return

    table = Table(title="Model Aliases", show_header=True, header_style="bold cyan")
    table.add_column("Alias", style="green")
    table.add_column("Model")

    for alias, model in sorted(aliases.items()):
        table.add_row(alias, model)

    console.print(table)


def alias_delete(
    name: Annotated[str, typer.Argument(help="Alias name to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete an alias.

    Example:
        miru alias delete g3
    """
    aliases = _load_aliases()

    if name not in aliases:
        console.print(f"[red bold]✗[/] Alias '{name}' não encontrado")
        sys.exit(1)

    if not force:
        console.print(f"[yellow]Deletar alias '{name}'?[/] Use --force para confirmar")
        return

    del aliases[name]
    _save_aliases(aliases)

    console.print(f"[green bold]✓[/] Alias '{name}' deletado")


def alias_show(
    name: Annotated[str, typer.Argument(help="Alias name")],
) -> None:
    """Show what an alias resolves to.

    Example:
        miru alias show g3
    """
    aliases = _load_aliases()

    if name not in aliases:
        console.print(f"[dim]'{name}' não é um alias[/]")
        console.print(f"[dim]Model name: {name}[/]")
        return

    console.print(f"[bold]Alias:[/] {name}")
    console.print(f"[bold]Model:[/] {aliases[name]}")


app = typer.Typer(help="Manage model aliases")
app.command("add")(alias_add)
app.command("list")(alias_list)
app.command("delete")(alias_delete)
app.command("show")(alias_show)


def alias() -> None:
    """Alias command group entry point."""
    app()
