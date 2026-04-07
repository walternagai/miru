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
from miru.core.i18n import t

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
        console.print(f"[red bold]✗[/] {t('config.unknown_key', key=key)}")
        console.print(f"[dim]{t('config.valid_keys')}")
        console.print(f"[dim]{t('config.valid_keys_more')}")
        console.print(f"[dim]{t('config.valid_keys_more2')}")
        console.print(f"[dim]{t('config.valid_keys_more3')}")
        console.print(f"[dim]{t('config.valid_keys_more4')}")
        sys.exit(1)

    if key in ("history_enabled", "verbose", "enable_tools", "enable_tavily"):
        if value.lower() in ("true", "1", "yes"):
            parsed_value = True
        elif value.lower() in ("false", "0", "no"):
            parsed_value = False
        else:
            console.print(f"[red bold]✗[/] {t('config.invalid_boolean', value=value)}")
            console.print(f"[dim]{t('config.valid_boolean')}")
            sys.exit(1)
    elif key == "tool_mode":
        if value not in ("manual", "auto", "auto_safe"):
            console.print(f"[red bold]✗[/] {t('config.invalid_tool_mode', value=value)}")
            console.print(f"[dim]{t('config.valid_tool_modes')}")
            sys.exit(1)
        parsed_value = value
    elif key in ("default_timeout", "default_temperature", "default_top_p"):
        try:
            parsed_value = float(value)
        except ValueError:
            console.print(f"[red bold]✗[/] {t('config.invalid_float', value=value)}")
            sys.exit(1)
    elif key in ("default_max_tokens", "default_top_k", "default_seed", "history_max_entries"):
        try:
            parsed_value = int(value)
        except ValueError:
            console.print(f"[red bold]✗[/] {t('config.invalid_integer', value=value)}")
            sys.exit(1)
    elif key == "tavily_api_key":
        if value and not value.startswith("tvly-"):
            console.print(f"[yellow]{t('config.api_key_format_warning')}[/]")
        parsed_value = value
    else:
        parsed_value = value

    setattr(config, key, parsed_value)
    save_config(config)

    console.print(f"[green bold]✓[/] {t('config.key_set', key=key, value=parsed_value)}")
    console.print(f"[dim]{t('config.config_file', path=CONFIG_FILE)}[/]")


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
        console.print(f"[red bold]✗[/] {t('config.unknown_key', key=key)}")
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

    table = Table(title=t("config.current"), show_header=True, header_style="bold cyan")
    table.add_column(t("config.key_header"), style="green")
    table.add_column(t("config.value_header"))
    table.add_column(t("config.source_header"), style="dim")

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

        if key == "tavily_api_key":
            display_value = t("config.api_key_hidden", last4=str(current_value)[-4:]) if current_value else t("config.api_key_not_set")
        else:
            display_value = str(current_value)

        source = t("config.source_default") if current_value == default_value else t("config.source_config")
        table.add_row(key, display_value, source)

    console.print(table)
    console.print(f"[dim]{t('config.config_file', path=CONFIG_FILE)}[/]")

    if config.profiles:
        console.print()
        console.print(f"[bold]{t('config.profiles_header')}[/]")
        for profile_name, profile_data in config.profiles.items():
            marker = f" [green]{t('config.profile_current')}[/]" if profile_name == config.current_profile else ""
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
            console.print(f"[yellow]{t('config.no_profiles')}[/]")
            console.print(f"[dim]{t('config.create_profile_hint')}[/]")
            return

        table = Table(title=t("config.profiles_header"), show_header=True, header_style="bold cyan")
        table.add_column(t("config.profile_header"), style="green")
        table.add_column(t("config.current_header"), justify="center")
        table.add_column(t("config.settings_header"))

        for profile_name, profile_data in config.profiles.items():
            is_current = "✓" if profile_name == config.current_profile else ""
            settings = ", ".join(f"{k}={v}" for k, v in profile_data.items())
            table.add_row(profile_name, is_current, settings)

        console.print(table)
        return

    if action == "switch":
        if not name:
            console.print(f"[red bold]✗[/] {t('config.profile_name_required')}")
            sys.exit(1)

        if name not in config.profiles:
            console.print(f"[red bold]✗[/] {t('config.profile_not_found', name=name)}")
            console.print(f"[dim]{t('config.available_profiles', profiles=', '.join(config.profiles.keys()))}")
            sys.exit(1)

        config.current_profile = name
        save_config(config)
        console.print(f"[green bold]✓[/] {t('config.profile_switched', name=name)}")
        return

    if action == "delete":
        if not name:
            console.print(f"[red bold]✗[/] {t('config.profile_name_required')}")
            sys.exit(1)

        if name not in config.profiles:
            console.print(f"[red bold]✗[/] {t('config.profile_not_found', name=name)}")
            sys.exit(1)

        del config.profiles[name]

        if config.current_profile == name:
            config.current_profile = None

        save_config(config)
        console.print(f"[green bold]✓[/] {t('config.profile_deleted', name=name)}")
        return

    if action == "create":
        if not name:
            console.print(f"[red bold]✗[/] {t('config.profile_name_required')}")
            sys.exit(1)

        if name in config.profiles:
            console.print(f"[red bold]✗[/] {t('config.profile_exists', name=name)}")
            sys.exit(1)

        config.profiles[name] = {}
        save_config(config)
        console.print(f"[green bold]✓[/] {t('config.profile_created', name=name)}")
        console.print(
            f"[dim]{t('config.add_settings_hint', name=name)}[/]"
        )
        return

    if action == "set":
        console.print(
            f"[red bold]✗[/] {t('config.profile_set_hint')}"
        )
        console.print(f"[dim]{t('config.edit_file_hint')}[/]")
        sys.exit(1)

    console.print(f"[red bold]✗[/] {t('config.invalid_action', action=action)}")
    console.print(f"[dim]{t('config.valid_actions')}")
    sys.exit(1)


@app.command("path")
def config_path() -> None:
    """Show configuration directory path."""
    console.print(f"{t('config.config_dir', path=CONFIG_DIR)}")
    console.print(f"{t('config.config_file_path', path=CONFIG_FILE)}")


@app.command("reset")
def config_reset(
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Reset configuration to defaults."""
    if not force:
        console.print(f"[yellow]{t('config.reset_warning')}[/]")
        console.print(f"[dim]{t('config.use_force')}[/]")
        return

    config = load_config()
    from miru.config_manager import Config

    fresh_config = Config()
    save_config(fresh_config)
    console.print(f"[green bold]✓[/] {t('config.reset_success')}")


def config() -> None:
    """Config command group entry point."""
    app()