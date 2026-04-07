"""Setup wizard for first-time users."""

import asyncio
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from miru.config_manager import CONFIG_FILE, ensure_config_dir, load_config, save_config
from miru.ollama.client import OllamaClient, OllamaConnectionError
from miru.core.i18n import t

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
    console.print(f"[bold cyan]{t('setup.title')}[/]")
    console.print("=" * 50)
    console.print()

    console.print(f"[dim]{t('setup.wizard_hint')}[/]")
    console.print()

    if not non_interactive:
        continue_setup = Confirm.ask(t('setup.continue'), default=True)
        if not continue_setup:
            console.print(f"[yellow]{t('setup.cancelled')}[/]")
            return

    console.print()
    console.print(f"[bold]{t('setup.step1')}[/]")
    console.print("-" * 40)

    ollama_running, version = await check_ollama(host)

    if ollama_running:
        console.print(f"[green bold]✓[/] {t('setup.ollama_running_version', version=version)}")
    else:
        console.print(f"[red bold]✗[/] {t('setup.cannot_connect', host=host)}")
        console.print()
        console.print(f"[yellow]{t('setup.ensure_ollama')}[/]")
        console.print(f"  1. {t('setup.install_ollama')}")
        console.print(f"  2. {t('setup.start_ollama')}")
        console.print()

        if non_interactive:
            console.print(f"[dim]{t('setup.run_setup_again')}[/]")
            return

        retry = Confirm.ask(t('setup.try_again'), default=True)
        if retry:
            console.print(f"[dim]{t('setup.waiting_ollama')}[/]")
            for _ in range(10):
                await asyncio.sleep(2)
                ollama_running, version = await check_ollama(host)
                if ollama_running:
                    console.print(f"[green bold]✓[/] {t('setup.ollama_running_version', version=version)}")
                    break

            if not ollama_running:
                console.print(f"[red bold]✗[/] {t('setup.still_not_accessible')}")
                console.print(f"[dim]{t('setup.run_setup_again')}[/]")
                return
        else:
            return

    console.print()

    console.print(f"[bold]{t('setup.step2')}[/]")
    console.print("-" * 40)

    models = await get_models(host)

    if not models:
        console.print(f"[yellow]{t('setup.no_models')}[/]")
        console.print()
        console.print(f"[dim]{t('setup.download_model')}[/]")
        console.print(f"[dim]{t('setup.popular_models')}[/]")
        console.print(f"  • {t('setup.gemma_desc')}")
        console.print(f"  • {t('setup.qwen_desc')}")
        console.print(f"  • {t('setup.llama_desc')}")
        console.print(f"  • {t('setup.llava_desc')}")
        console.print()

        if non_interactive:
            console.print(f"[dim]{t('setup.run_setup_again')}[/]")
            return

        download = Prompt.ask(t('setup.which_model'), default="gemma3:latest")

        console.print(f"[dim]{t('setup.downloading', model=download)}[/]")
        console.print(f"[dim]{t('setup.download_hint', model=download)}[/]")

        return

    console.print(f"[dim]{t('setup.available_models', count=len(models))}[/]")
    for i, model in enumerate(models[:5], 1):
        console.print(f"  {i}. {model}")
    if len(models) > 5:
        console.print(f"  {t('setup.and_more', count=len(models) - 5)}")

    console.print()

    if non_interactive:
        default_model = models[0]
        console.print(f"[dim]{t('setup.using_first_model', model=default_model)}[/]")
    else:
        default_model = Prompt.ask(
            t('setup.select_default'),
            default=models[0] if models else "",
            show_default=True,
        )

        if default_model not in models:
            console.print(f"[yellow]{t('setup.model_not_found', model=default_model)}[/]")
            use_anyway = Confirm.ask(t('setup.use_anyway'), default=False)
            if not use_anyway:
                default_model = models[0] if models else None

    console.print()

    console.print(f"[bold]{t('setup.step3')}[/]")
    console.print("-" * 40)

    config = load_config()

    if default_model:
        config.default_model = default_model
        config.default_host = host

    if not non_interactive:
        enable_history = Confirm.ask(t('setup.enable_history'), default=True)
        config.history_enabled = enable_history

        if enable_history:
            max_entries = Prompt.ask(
                t('setup.max_entries'),
                default=str(config.history_max_entries),
            )
            try:
                config.history_max_entries = int(max_entries)
            except ValueError:
                pass

        verbose_mode = Confirm.ask(t('setup.enable_verbose'), default=False)
        config.verbose = verbose_mode

        if Confirm.ask(t('setup.create_alias'), default=False):
            alias_name = Prompt.ask(
                t('setup.alias_name'), default="g3" if "gemma" in default_model else "qwen"
            )
            alias_model = Prompt.ask(t('setup.model_to_alias'), default=default_model)

            from miru.alias import _save_aliases, _load_aliases

            aliases = _load_aliases()
            aliases[alias_name] = alias_model
            _save_aliases(aliases)
            console.print(f"[green]✓[/] {t('setup.alias_created', alias=alias_name, model=alias_model)}")

    save_config(config)

    console.print()
    console.print(f"[bold]{t('setup.step4')}[/]")
    console.print("-" * 40)

    console.print(f"[dim]{t('setup.config_file_label')}[/] " + str(CONFIG_FILE))
    console.print(f"[dim]{t('setup.default_model_label')}[/] {config.default_model}")
    console.print(f"[dim]{t('setup.host_label')}[/] {config.default_host}")
    console.print(f"[dim]{t('setup.history_enabled_label')}[/] {config.history_enabled}")
    console.print()

    console.print(f"[green bold]✓ {t('setup.complete')}[/]")
    console.print()
    console.print(f"[bold]{t('setup.next_steps')}[/]")
    console.print(f"  • {t('setup.try_chat')}")
    console.print(f"  • {t('setup.try_run')}")
    console.print(f"  • {t('setup.see_commands')}")
    console.print()


def setup(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    non_interactive: Annotated[
        bool, typer.Option("--non-interactive", "-y", help="Non-interactive mode")
    ] = False,
) -> None:
    """Run the setup wizard for first-time users.

    \b
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
        console.print(f"[yellow]{t('setup.cancelled')}[/]")
        sys.exit(0)