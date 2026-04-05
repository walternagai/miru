"""miru list command - list available models."""

import asyncio
from typing import Any, Optional

import typer

from miru.config import get_host
from miru.ollama.client import OllamaClient, OllamaConnectionError
from miru.renderer import (
    render_empty_models,
    render_error,
    render_models_json,
    render_models_table,
)


def list_models(
    host: Optional[str] = typer.Option(
        None,
        "--host",
        "-h",
        help="Ollama host URL (default: http://localhost:11434)",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: text or json",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output for pipes and scripts",
    ),
) -> None:
    """
    List available models from Ollama server.

    Examples:
        miru list
        miru list --format json
        miru list --quiet | head -5
    """
    ollama_host = get_host(host)

    try:
        models = asyncio.run(_list_models_async(ollama_host))

        if not models:
            render_empty_models()
            raise typer.Exit(code=0)

        if format == "json":
            render_models_json(models, quiet=quiet)
        else:
            render_models_table(models, quiet=quiet)

    except OllamaConnectionError:
        render_error(
            f"Não foi possível conectar ao Ollama em {ollama_host}",
            "Verifique se o Ollama está rodando: ollama serve",
        )
        raise typer.Exit(code=1)


async def _list_models_async(host: str) -> list[dict[str, Any]]:
    """Fetch models from Ollama server."""
    async with OllamaClient(host=host) as client:
        return await client.list_models()