"""CLI entry point for miru."""

import typer

from miru import __version__
from miru.alias import app as alias_app
from miru.commands.batch import batch
from miru.commands.chat import chat
from miru.commands.compare import compare
from miru.commands.config_cmd import app as config_app
from miru.commands.copy import copy
from miru.commands.delete import delete
from miru.commands.embed import embed
from miru.commands.history_cmd import history_cmd, history_show
from miru.commands.info import info
from miru.commands.list import list_models
from miru.commands.logs import clear_logs, logs
from miru.commands.pull import pull
from miru.commands.run import run
from miru.commands.status import ps, search, status, stop
from miru.completion import completion
from miru.template import app as template_app

app = typer.Typer(
    name="miru",
    help="CLI Python para servidor Ollama local",
    add_completion=False,
)


@app.command()
def version() -> None:
    """Show miru version."""
    typer.echo(f"miru {__version__}")


@app.command("list")
def list_cmd(
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    """List available models.

    Examples:
        miru list
        miru list --format json
        miru list --quiet
    """
    list_models(host=host, format=format, quiet=quiet)


@app.command("info")
def info_cmd(
    model: str = typer.Argument(..., help="Model name"),
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    """Show detailed model information.

    Examples:
        miru info gemma3:latest
        miru info llava --format json
    """
    info(model=model, host=host, format=format, quiet=quiet)


@app.command("pull")
def pull_cmd(
    model: str = typer.Argument(..., help="Model name to download"),
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    """Download a model from registry.

    Examples:
        miru pull gemma3:latest
        miru pull llava:latest --quiet
    """
    pull(model=model, host=host, quiet=quiet)


@app.command("run")
def run_cmd(
    model: str = typer.Argument(..., help="Model name"),
    prompt: str = typer.Argument(..., help="Prompt text"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
    system_file: str | None = typer.Option(None, "--system-file", help="System prompt file"),
    image: list[str] = typer.Option([], "--image", "-i", help="Image file (repeatable)"),
    file: list[str] = typer.Option([], "--file", "-f", help="File to include (repeatable)"),
    audio: str | None = typer.Option(None, "--audio", "-a", help="Audio file"),
    temperature: float | None = typer.Option(None, help="Sampling temperature"),
    top_p: float | None = typer.Option(None, help="Nucleus sampling"),
    top_k: int | None = typer.Option(None, help="Top-k sampling"),
    max_tokens: int | None = typer.Option(None, help="Max tokens"),
    seed: int | None = typer.Option(None, help="Random seed"),
    repeat_penalty: float | None = typer.Option(None, help="Repetition penalty"),
    ctx: int | None = typer.Option(None, help="Context window"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    host: str | None = typer.Option(None, "--host", help="Ollama host URL"),
    format: str = typer.Option("text", "--format", help="Output format (text/json)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate text with a single prompt.

    Examples:
        miru run gemma3:latest "Explain recursion"
        miru run llava:latest "Describe" --image photo.jpg
        miru run qwen2.5 --system "Be concise" "What is Python?"
    """
    run(
        model=model,
        prompt=prompt,
        system=system,
        system_file=system_file,
        image=image,
        file=file,
        audio=audio,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_tokens=max_tokens,
        seed=seed,
        repeat_penalty=repeat_penalty,
        ctx=ctx,
        no_stream=no_stream,
        host=host,
        format=format,
        quiet=quiet,
    )


@app.command("chat")
def chat_cmd(
    model: str | None = typer.Argument(None, help="Model name"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
    system_file: str | None = typer.Option(None, "--system-file", help="System prompt file"),
    temperature: float | None = typer.Option(None, help="Sampling temperature"),
    top_p: float | None = typer.Option(None, help="Nucleus sampling"),
    top_k: int | None = typer.Option(None, help="Top-k sampling"),
    max_tokens: int | None = typer.Option(None, help="Max tokens"),
    seed: int | None = typer.Option(None, help="Random seed"),
    repeat_penalty: float | None = typer.Option(None, help="Repetition penalty"),
    ctx: int | None = typer.Option(None, help="Context window"),
    host: str | None = typer.Option(None, "--host", help="Ollama host URL"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
) -> None:
    """Start interactive chat session.

    Chat commands:
        /exit, /quit   - End session
        /clear         - Clear history
        /history       - Show turn count
        /stats         - Show session statistics
        /model <name>  - Switch model
        /system <p>    - Change system prompt
        /retry         - Retry last prompt
        /save <file>   - Save conversation
        /help          - Show commands

    Examples:
        miru chat gemma3:latest
        miru chat --system "You are a helpful assistant"
    """
    chat(
        model=model,
        system=system,
        system_file=system_file,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_tokens=max_tokens,
        seed=seed,
        repeat_penalty=repeat_penalty,
        ctx=ctx,
        host=host,
        quiet=quiet,
    )


app.command("compare")(compare)
app.command("delete")(delete)
app.command("copy")(copy)
app.command("embed")(embed)
app.command("batch")(batch)


@app.command("status")
def status_cmd(
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
) -> None:
    """Check Ollama server status and running models.

    Examples:
        miru status
        miru status --verbose
    """
    status(host=host, verbose=verbose)


@app.command("ps")
def ps_cmd(
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
) -> None:
    """List models currently loaded in VRAM.

    Examples:
        miru ps
        miru ps --format json
    """
    ps(host=host, format=format)


@app.command("stop")
def stop_cmd(
    model: str = typer.Argument(..., help="Model name to unload"),
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    force: bool = typer.Option(False, "--force", "-f", help="Force immediate unload"),
) -> None:
    """Unload a model from VRAM.

    Examples:
        miru stop gemma3:latest
        miru stop llava --force
    """
    stop(model=model, host=host, force=force)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    host: str | None = typer.Option(None, "--host", "-h", help="Ollama host URL"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
) -> None:
    """Search for models locally (filter by name).

    Examples:
        miru search gemma
        miru search llama --format json
    """
    search(query=query, host=host, format=format)


@app.command("history")
def history_main(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries"),
    command: str | None = typer.Option(None, "--command", "-c", help="Filter by command"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search query"),
    clear: bool = typer.Option(False, "--clear", help="Clear all history"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text/json)"),
) -> None:
    """View and manage prompt history.

    Examples:
        miru history
        miru history --limit 50
        miru history --command run
        miru history --search "python"
        miru history --clear
    """
    history_cmd(limit=limit, command=command, search=search, clear=clear, format=format)


@app.command("history-show")
def history_show_cmd(
    index: int = typer.Argument(0, help="History entry index"),
) -> None:
    """Show detailed history entry.

    Example:
        miru history-show 0
    """
    history_show(index=index)


@app.command("logs")
def logs_cmd(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines"),
    latest: bool = typer.Option(False, "--latest", "-l", help="Show only latest log"),
    list: bool = typer.Option(False, "--list", help="List log files"),
) -> None:
    """View execution logs.

    Examples:
        miru logs
        miru logs --lines 100
        miru logs --follow
        miru logs --latest
        miru logs --list
    """
    logs(follow=follow, lines=lines, latest=latest, list_files=list)


@app.command("logs-clear")
def logs_clear_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Clear all logs.

    Example:
        miru logs-clear --force
    """
    clear_logs(force=force)


app.add_typer(config_app, name="config")
app.add_typer(template_app, name="template")
app.add_typer(alias_app, name="alias")

app.command("completion")(completion)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
