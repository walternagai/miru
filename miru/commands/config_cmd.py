"""Config command for managing CLI configuration."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.config_manager import (
    CONFIG_DIR,
    CONFIG_FILE,
    load_config,
    save_config,
)

console = Console()
app = typer.Typer(help="Manage miru configuration")


@app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value.

    Examples:
        miru config set default_host http://localhost:11434
        miru config set default_model gemma3:latest
        miru config set default_temperature 0.7
        miru config set history_max_entries 500
    """
    config = load_config()

    if not hasattr(config, key):
        console.print(f"[red bold]✗[/] Unknown config key: {key}")
        console.print("[dim]Valid keys: default_host, default_model, default_timeout,")
        console.print("[dim]  default_temperature, default_max_tokens, default_top_p,")
        console.print("[dim]  default_top_k, default_seed, history_enabled,")
        console.print("[dim]  history_max_entries, verbose, tavily_api_key,")
        console.print("[dim]  enable_tools, enable_tavily, tool_mode, sandbox_dir")
        sys.exit(1)

    # Parse value based on key type
    if key in ("history_enabled", "verbose", "enable_tools", "enable_tavily"):
        # Boolean keys
        if value.lower() in ("true", "1", "yes"):
            parsed_value = True
        elif value.lower() in ("false", "0", "no"):
            parsed_value = False
        else:
            console.print(f"[red bold]✗[/] Invalid boolean value: {value}")
            console.print("[dim]Valid values: true, false, 1, 0, yes, no")
            sys.exit(1)
    elif key == "tool_mode":
        # Validate tool_mode
        if value not in ("manual", "auto", "auto_safe"):
            console.print(f"[red bold]✗[/] Invalid tool_mode: {value}")
            console.print("[dim]Valid values: manual, auto, auto_safe")
            sys.exit(1)
        parsed_value = value
    elif key in ("default_timeout", "default_temperature", "default_top_p"):
        try:
            parsed_value = float(value)
        except ValueError:
            console.print(f"[red bold]✗[/] Invalid float value: {value}")
            sys.exit(1)
    elif key in ("default_max_tokens", "default_top_k", "default_seed", "history_max_entries"):
        try:
            parsed_value = int(value)
        except ValueError:
            console.print(f"[red bold]✗[/] Invalid integer value: {value}")
            sys.exit(1)
    elif key == "tavily_api_key":
        # Validate API key format
        if value and not value.startswith("tvly-"):
            console.print("[yellow]Warning: API key doesn't match expected format (tvly-...)[/]")
        parsed_value = value
    else:
        parsed_value = value

    setattr(config, key, parsed_value)
    save_config(config)

    console.print(f"[green bold]✓[/] Set {key} = {parsed_value}")
    console.print(f"[dim]Config file: {CONFIG_FILE}[/]")


@app.command("get")
def config_get(
    key: Annotated[str, typer.Argument(help="Configuration key")],
) -> None:
    """Get a configuration value.

    Examples:
        miru config get default_host
        miru config get default_model
    """
    config = load_config()

    if not hasattr(config, key):
        console.print(f"[red bold]✗[/] Unknown config key: {key}")
        sys.exit(1)

    value = getattr(config, key)
    console.print(f"{key} = {value}")


@app.command("list")
def config_list() -> None:
    """List all configuration values.

    Example:
        miru config list
    """
    config = load_config()

    table = Table(title="Miru Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Key", style="green")
    table.add_column("Value")
    table.add_column("Source", style="dim")

    defaults = {
        "default_host": "http://localhost:11434",
        "default_model": None,
        "default_timeout": 30.0,
        "default_temperature": None,
        "default_max_tokens": None,
        "default_top_p": None,
        "default_top_k": None,
        "default_seed": None,
        "history_enabled": True,
        "history_max_entries": 1000,
        "verbose": False,
        "tavily_api_key": None,
        "enable_tools": False,
        "enable_tavily": False,
        "tool_mode": "auto_safe",
        "sandbox_dir": None,
    }

    for key, default_value in defaults.items():
        current_value = getattr(config, key)

        # Hide API key for security
        if key == "tavily_api_key":
            display_value = f"***{str(current_value)[-4:]}" if current_value else "Not set"
        else:
            display_value = str(current_value)

        source = "default" if current_value == default_value else "config"
        table.add_row(key, display_value, source)

    console.print(table)
    console.print(f"[dim]Config file: {CONFIG_FILE}[/]")

    if config.profiles:
        console.print()
        console.print("[bold]Profiles:[/]")
        for profile_name, profile_data in config.profiles.items():
            marker = " [green](current)[/]" if profile_name == config.current_profile else ""
            console.print(f"  • {profile_name}{marker}")
            for k, v in profile_data.items():
                console.print(f"    {k}: {v}")


@app.command("profile")
def config_profile(
    action: Annotated[str, typer.Argument(help="Action: create, switch, delete, list")],
    name: Annotated[str | None, typer.Argument(help="Profile name")] = None,
) -> None:
    """Manage configuration profiles.

    Examples:
        miru config profile create work --set default_host=http://server:11434
        miru config profile switch work
        miru config profile delete work
        miru config profile list
    """
    config = load_config()

    if action == "list":
        if not config.profiles:
            console.print("[yellow]No profiles configured.[/]")
            console.print("[dim]Create one: miru config profile create <name>[/]")
            return

        table = Table(title="Configuration Profiles", show_header=True, header_style="bold cyan")
        table.add_column("Profile", style="green")
        table.add_column("Current", justify="center")
        table.add_column("Settings")

        for profile_name, profile_data in config.profiles.items():
            is_current = "✓" if profile_name == config.current_profile else ""
            settings = ", ".join(f"{k}={v}" for k, v in profile_data.items())
            table.add_row(profile_name, is_current, settings)

        console.print(table)
        return

    if action == "switch":
        if not name:
            console.print("[red bold]✗[/] Profile name required.")
            sys.exit(1)

        if name not in config.profiles:
            console.print(f"[red bold]✗[/] Profile '{name}' not found.")
            console.print("[dim]Available profiles: " + ", ".join(config.profiles.keys()))
            sys.exit(1)

        config.current_profile = name
        save_config(config)
        console.print(f"[green bold]✓[/] Switched to profile '{name}'")
        return

    if action == "delete":
        if not name:
            console.print("[red bold]✗[/] Profile name required.")
            sys.exit(1)

        if name not in config.profiles:
            console.print(f"[red bold]✗[/] Profile '{name}' not found.")
            sys.exit(1)

        del config.profiles[name]

        if config.current_profile == name:
            config.current_profile = None

        save_config(config)
        console.print(f"[green bold]✓[/] Deleted profile '{name}'")
        return

    if action == "create":
        if not name:
            console.print("[red bold]✗[/] Profile name required.")
            sys.exit(1)

        if name in config.profiles:
            console.print(f"[red bold]✗[/] Profile '{name}' already exists.")
            sys.exit(1)

        config.profiles[name] = {}
        save_config(config)
        console.print(f"[green bold]✓[/] Created profile '{name}'")
        console.print(
            f"[dim]Add settings: miru config profile set {name} default_host http://server:11434[/]"
        )
        return

    if action == "set":
        console.print(
            "[red bold]✗[/] Use: miru config set <key> <value> (profiles are auto-detected)[/]"
        )
        console.print("[dim]Or edit the config file directly[/]")
        sys.exit(1)

    console.print(f"[red bold]✗[/] Invalid action: {action}")
    console.print("[dim]Valid actions: create, switch, delete, list[/]")
    sys.exit(1)


@app.command("path")
def config_path() -> None:
    """Show configuration directory path."""
    console.print(f"Config directory: {CONFIG_DIR}")
    console.print(f"Config file: {CONFIG_FILE}")


@app.command("reset")
def config_reset(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Reset configuration to defaults."""
    if not force:
        console.print("[yellow]This will reset all configuration to defaults.[/]")
        console.print("[dim]Use --force to confirm[/]")
        return

    config = load_config()
    from miru.config_manager import Config

    fresh_config = Config()
    save_config(fresh_config)
    console.print("[green bold]✓[/] Configuration reset to defaults")


def config() -> None:
    """Config command group entry point."""
    app()
