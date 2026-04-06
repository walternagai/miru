"""Setup wizard for first-time users."""

import asyncio
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from miru.config_manager import CONFIG_FILE, ensure_config_dir, load_config, save_config
from miru.ollama.client import OllamaClient, OllamaConnectionError

console = Console()


async def check_ollama(host: str) -> tuple[bool, str]:
    """Check if Ollama is running and accessible."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/")
            if response.status_code == 200:
                version_response = await client.get(f"{host}/api/version")
                version = "unknown"
                if version_response.status_code == 200:
                    version_data = version_response.json()
                    version = version_data.get("version", "unknown")
                return True, version
        return False, ""
    except Exception:
        return False, ""


async def get_models(host: str) -> list[str]:
    """Get list of available models."""
    try:
        async with OllamaClient(host) as client:
            models = await client.list_models()
            return [m.get("name", "") for m in models]
    except Exception:
        return []


async def setup_async(host: str, non_interactive: bool) -> None:
    """Run setup wizard."""
    console.print()
    console.print("[bold cyan]miru Setup Wizard[/]")
    console.print("=" * 50)
    console.print()

    console.print("[dim]This wizard will help you configure miru CLI for first use.[/]")
    console.print()

    if not non_interactive:
        continue_setup = Confirm.ask("Continue with setup?", default=True)
        if not continue_setup:
            console.print("[yellow]Setup cancelled.[/]")
            return

    console.print()
    console.print("[bold]Step 1: Check Ollama Connection[/]")
    console.print("-" * 40)

    ollama_running, version = await check_ollama(host)

    if ollama_running:
        console.print(f"[green bold]✓[/] Ollama is running (version {version})")
    else:
        console.print(f"[red bold]✗[/] Cannot connect to Ollama at {host}")
        console.print()
        console.print("[yellow]Make sure Ollama is installed and running:[/]")
        console.print("  1. Install Ollama: https://ollama.ai")
        console.print("  2. Start Ollama: ollama serve")
        console.print()

        if non_interactive:
            console.print("[dim]Run 'miru setup' again after starting Ollama.[/]")
            return

        retry = Confirm.ask("Try again?", default=True)
        if retry:
            console.print("[dim]Waiting for Ollama...[/]")
            for _ in range(10):
                await asyncio.sleep(2)
                ollama_running, version = await check_ollama(host)
                if ollama_running:
                    console.print(f"[green bold]✓[/] Ollama is running (version {version})")
                    break

            if not ollama_running:
                console.print("[red bold]✗[/] Ollama is still not accessible")
                console.print("[dim]Run 'miru setup' again after starting Ollama.[/]")
                return
        else:
            return

    console.print()

    console.print("[bold]Step 2: Select Default Model[/]")
    console.print("-" * 40)

    models = await get_models(host)

    if not models:
        console.print("[yellow]No models found.[/]")
        console.print()
        console.print("[dim]Download a model with: miru pull <model>[/]")
        console.print("[dim]Popular models:[/]")
        console.print("  • gemma3:latest - Fast, efficient (4B)")
        console.print("  • qwen2.5:7b - Good balance (7B)")
        console.print("  • llama3.2:latest - Large model (8B)")
        console.print("  • llava:latest - Vision model")
        console.print()

        if non_interactive:
            console.print("[dim]Run 'miru setup' again after downloading a model.[/]")
            return

        download = Prompt.ask("Which model to download?", default="gemma3:latest")

        console.print(f"[dim]Downloading {download}...[/]")
        console.print("[dim]Run: miru pull " + download + "[/]")

        return

    console.print(f"[dim]Available models ({len(models)}):[/]")
    for i, model in enumerate(models[:5], 1):
        console.print(f"  {i}. {model}")
    if len(models) > 5:
        console.print(f"  ... and {len(models) - 5} more")

    console.print()

    if non_interactive:
        default_model = models[0]
        console.print(f"[dim]Using first model as default: {default_model}[/]")
    else:
        default_model = Prompt.ask(
            "Select default model",
            default=models[0] if models else "",
            show_default=True,
        )

        if default_model not in models:
            console.print(f"[yellow]Model '{default_model}' not found locally.[/]")
            use_anyway = Confirm.ask("Use this model name anyway?", default=False)
            if not use_anyway:
                default_model = models[0] if models else None

    console.print()

    console.print("[bold]Step 3: Configure Settings[/]")
    console.print("-" * 40)

    config = load_config()

    if default_model:
        config.default_model = default_model
        config.default_host = host

    if not non_interactive:
        enable_history = Confirm.ask("Enable prompt history?", default=True)
        config.history_enabled = enable_history

        if enable_history:
            max_entries = Prompt.ask(
                "Maximum history entries",
                default=str(config.history_max_entries),
            )
            try:
                config.history_max_entries = int(max_entries)
            except ValueError:
                pass

        verbose_mode = Confirm.ask("Enable verbose mode by default?", default=False)
        config.verbose = verbose_mode

        if Confirm.ask("Create an alias for quick access?", default=False):
            alias_name = Prompt.ask(
                "Alias name", default="g3" if "gemma" in default_model else "qwen"
            )
            alias_model = Prompt.ask("Model to alias", default=default_model)

            from miru.alias import _save_aliases, _load_aliases

            aliases = _load_aliases()
            aliases[alias_name] = alias_model
            _save_aliases(aliases)
            console.print(f"[green]✓[/] Alias '{alias_name}' -> '{alias_model}' created")

    save_config(config)

    console.print()
    console.print("[bold]Step 4: Verify Installation[/]")
    console.print("-" * 40)

    console.print("[dim]Configuration file:[/] " + str(CONFIG_FILE))
    console.print(f"[dim]Default model:[/] {config.default_model}")
    console.print(f"[dim]Host:[/] {config.default_host}")
    console.print(f"[dim]History enabled:[/] {config.history_enabled}")
    console.print()

    console.print("[green bold]✓ Setup complete![/]")
    console.print()
    console.print("[bold]Next steps:[/]")
    console.print("  • Try: miru chat")
    console.print("  • Try: miru run gemma3 'Hello'")
    console.print("  • See all commands: miru --help")
    console.print()


def setup(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    non_interactive: Annotated[
        bool, typer.Option("--non-interactive", "-y", help="Non-interactive mode")
    ] = False,
) -> None:
    """Run the setup wizard for first-time users.

    Examples:
        miru setup
        miru setup --host http://localhost:11434
        miru setup --non-interactive
    """
    from miru.config import get_host

    resolved_host = host or get_host()

    try:
        asyncio.run(setup_async(resolved_host, non_interactive))
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Setup cancelled.[/]")
        sys.exit(0)
