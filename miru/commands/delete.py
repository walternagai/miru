"""miru delete command - delete models from local storage.

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


async def _delete_async(host: str, model: str, force: bool) -> None:
    """Async implementation of delete command."""
    set_language("en_US")
    
    async with OllamaClient(host) as client:
        try:
            models = await client.list_models()
            model_names = [m.get("name", "") for m in models]

            if model not in model_names:
                error = ModelNotFoundError(model, model_names[:5])
                render_error(error.message, error.suggestion)
                raise typer.Exit(code=1)
        except Exception as e:
            if "connection" in str(e).lower():
                error = MiruConnectionError(host)
                render_error(error.message, error.suggestion)
            else:
                render_error(str(e))
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(f"Delete '{model}'?")
            if not confirm:
                typer.echo("Cancelled.")
                raise typer.Exit(code=0)

        try:
            await client.delete_model(model)
            render_success(t("success.model_deleted", model=model))
        except Exception:
            error = ModelNotFoundError(model)
            render_error(error.message, error.suggestion)
            raise typer.Exit(code=1)


def delete(
    model: str = typer.Argument(..., help="Model name to delete"),
    host: Host = None,
    force: Force = False,
) -> None:
    """Delete a model from local storage.

    Examples:
        miru delete gemma3:latest
        miru delete gemma3:latest --force
    """
    model = resolve_alias(model)
    resolved_host = resolve_host(host)

    try:
        asyncio.run(_delete_async(resolved_host, model, force))
    except KeyboardInterrupt:
        raise typer.Exit(code=0)