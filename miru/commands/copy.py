"""miru copy command - copy/clone models.

Refactored with i18n support.
"""

import asyncio

import typer

from miru.alias import resolve_alias
from miru.cli_options import Force, Host
from miru.core.config import resolve_host
from miru.core.errors import ModelNotFoundError, ConnectionError as MiruConnectionError
from miru.core.i18n import t, set_language
from miru.ollama.client import OllamaClient
from miru.ui.render import render_error, render_success


async def _copy_async(host: str, source: str, destination: str, force: bool) -> None:
    """Async implementation of copy command."""
    set_language("en_US")
    
    async with OllamaClient(host) as client:
        try:
            models = await client.list_models()
            model_names = [m.get("name", "") for m in models]

            if source not in model_names:
                error = ModelNotFoundError(source, model_names[:5])
                render_error(error.message, error.suggestion)
                raise typer.Exit(code=1)

            if destination in model_names and not force:
                render_error(
                    f"Model '{destination}' already exists.",
                    "Use --force to overwrite.",
                )
                raise typer.Exit(code=1)

        except Exception as e:
            if "connection" in str(e).lower():
                error = MiruConnectionError(host)
                render_error(error.message, error.suggestion)
            else:
                render_error(str(e))
            raise typer.Exit(code=1)

        try:
            await client.copy_model(source, destination)

            models_after = await client.list_models()
            model_info = next((m for m in models_after if m["name"] == destination), None)

            if model_info:
                size_gb = model_info.get("size", 0) / (1024**3)
                render_success(f"Copied: {source} → {destination} ({size_gb:.2f} GB)")
            else:
                render_success(f"Copied: {source} → {destination}")

        except Exception:
            error = ModelNotFoundError(source)
            render_error(error.message, error.suggestion)
            raise typer.Exit(code=1)


def copy(
    source: str = typer.Argument(..., help="Source model name"),
    destination: str = typer.Argument(..., help="New model name"),
    host: Host = None,
    force: Force = False,
) -> None:
    """Copy a model to a new name.

    Examples:
        miru copy gemma3:latest gemma3-backup
        miru copy gemma3:latest my-gemma --force
    """
    source = resolve_alias(source)
    resolved_host = resolve_host(host)

    try:
        asyncio.run(_copy_async(resolved_host, source, destination, force))
    except KeyboardInterrupt:
        raise typer.Exit(code=0)