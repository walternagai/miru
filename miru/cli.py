"""CLI entry point for miru."""

import typer

from miru import __version__
from miru.commands.chat import chat
from miru.commands.info import info
from miru.commands.list import list_models
from miru.commands.pull import pull
from miru.commands.run import run

app = typer.Typer(
    name="miru",
    help="CLI Python para servidor Ollama local",
    add_completion=False,
)


@app.command()
def version() -> None:
    """Show miru version."""
    typer.echo(f"miru {__version__}")


# Register commands from submodules
app.command(name="list")(list_models)
app.command(name="info")(info)
app.command(name="pull")(pull)
app.command(name="run")(run)
app.command(name="chat")(chat)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()