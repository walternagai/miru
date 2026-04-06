"""miru delete command - delete models from local storage."""

import asyncio

import typer

from miru.config import get_host
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.renderer import render_error, render_success


async def _delete_async(host: str, model: str, force: bool) -> None:
    """Async implementation of delete command."""
    async with OllamaClient(host) as client:
        try:
            models = await client.list_models()
            model_names = [m.get("name", "") for m in models]

            if model not in model_names:
                render_error(
                    f'Modelo "{model}" não encontrado localmente.',
                    "Modelos disponíveis: miru list",
                )
                raise typer.Exit(code=1)
        except OllamaConnectionError as e:
            render_error(str(e))
            raise typer.Exit(code=1)

        if not force:
            confirm = typer.confirm(f"Tem certeza que deseja deletar '{model}'?")
            if not confirm:
                typer.echo("Cancelado.")
                raise typer.Exit(code=0)

        try:
            await client.delete_model(model)
            render_success(f"Modelo '{model}' deletado com sucesso.")
        except OllamaModelNotFound:
            render_error(f'Modelo "{model}" não encontrado.')
            raise typer.Exit(code=1)


def delete(
    model: str = typer.Argument(..., help="Model name to delete"),
    host: str | None = typer.Option(
        None, "--host", "-h", help="Ollama host URL (default: http://localhost:11434)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a model from local storage.

    Examples:
        miru delete gemma3:latest
        miru delete gemma3:latest --force
    """
    resolved_host = get_host(host)

    try:
        asyncio.run(_delete_async(resolved_host, model, force))
    except OllamaConnectionError as e:
        render_error(str(e))
        raise typer.Exit(code=1)
