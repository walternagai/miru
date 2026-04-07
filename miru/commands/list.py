"""miru list command - list available models.

Refactored with i18n support.
"""

import asyncio
from typing import Any

import typer

from miru.cli_options import Host, Format, Quiet
from miru.core.config import resolve_host
from miru.core.errors import ConnectionError as MiruConnectionError
from miru.core.i18n import t
from miru.ollama.client import OllamaClient
from miru.renderer import (
    render_empty_models,
    render_error,
    render_models_json,
    render_models_table,
)


def list_models(
    host: Host = None,
    format: Format = "text",
    quiet: Quiet = False,
) -> None:
    """
    List available models from Ollama server.

    Examples:
        miru list
        miru list --format json
        miru list --quiet | head -5
    """
    ollama_host = resolve_host(host)

    try:
        models = asyncio.run(_list_models_async(ollama_host))

        if not models:
            render_empty_models()
            raise typer.Exit(code=0)

        # Sort models alphabetically by name
        models = sorted(models, key=lambda m: m.get("name", ""))

        if format == "json":
            render_models_json(models, quiet=quiet)
        else:
            render_models_table(models, quiet=quiet)

    except MiruConnectionError:
        error = MiruConnectionError(ollama_host)
        render_error(error.message, error.suggestion)
        raise typer.Exit(code=1)


async def _list_models_async(host: str) -> list[dict[str, Any]]:
    """Fetch models from Ollama server."""
    async with OllamaClient(host=host) as client:
        return await client.list_models()