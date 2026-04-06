"""miru copy command - copy/clone models."""

import asyncio

import typer

from miru.config import get_host
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.renderer import render_error, render_success


async def _copy_async(host: str, source: str, destination: str, force: bool) -> None:
    """Async implementation of copy command."""
    async with OllamaClient(host) as client:
        try:
            models = await client.list_models()
            model_names = [m.get("name", "") for m in models]

            if source not in model_names:
                render_error(
                    f'Modelo de origem "{source}" não encontrado.',
                    "Modelos disponíveis: miru list",
                )
                raise typer.Exit(code=1)

            if destination in model_names and not force:
                render_error(
                    f'Modelo "{destination}" já existe.',
                    "Use --force para sobrescrever.",
                )
                raise typer.Exit(code=1)

        except OllamaConnectionError as e:
            render_error(str(e))
            raise typer.Exit(code=1)

        try:
            await client.copy_model(source, destination)

            models_after = await client.list_models()
            model_info = next((m for m in models_after if m["name"] == destination), None)

            if model_info:
                size_gb = model_info.get("size", 0) / (1024**3)
                render_success(f"Copiado: {source} → {destination} ({size_gb:.2f} GB)")
            else:
                render_success(f"Copiado: {source} → {destination}")

        except OllamaModelNotFound:
            render_error(f'Modelo "{source}" não encontrado.')
            raise typer.Exit(code=1)


def copy(
    source: str = typer.Argument(..., help="Source model name"),
    destination: str = typer.Argument(..., help="New model name"),
    host: str | None = typer.Option(
        None, "--host", "-h", help="Ollama host URL (default: http://localhost:11434)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite destination if exists"),
) -> None:
    """Copy a model to a new name.

    Examples:
        miru copy gemma3:latest gemma3-backup
        miru copy gemma3:latest my-gemma --force
    """
    resolved_host = get_host(host)

    try:
        asyncio.run(_copy_async(resolved_host, source, destination, force))
    except OllamaConnectionError as e:
        render_error(str(e))
        raise typer.Exit(code=1)
