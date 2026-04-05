"""miru info command - show model information."""

import asyncio
from typing import Any, Optional

import typer

from miru.config import get_host
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.renderer import (
    render_error,
    render_model_info,
    render_model_info_json,
)


def info(
    model: str = typer.Argument(..., help="Model name (e.g., gemma3:latest)"),
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
    Show detailed information about a model.

    Examples:
        miru info gemma3:latest
        miru info llava --format json
    """
    ollama_host = get_host(host)

    try:
        model_data, capabilities_data = asyncio.run(
            _get_model_info_async(ollama_host, model)
        )

        if format == "json":
            render_model_info_json(model_data, capabilities_data, quiet=quiet)
        else:
            render_model_info(model, model_data, capabilities_data, quiet=quiet)

    except OllamaModelNotFound:
        render_error(
            f'Modelo "{model}" não encontrado.',
            f"Modelos disponíveis: miru list\n  Para baixar: miru pull {model}",
        )
        raise typer.Exit(code=1)
    except OllamaConnectionError:
        render_error(
            f"Não foi possível conectar ao Ollama em {ollama_host}",
            "Verifique se o Ollama está rodando: ollama serve",
        )
        raise typer.Exit(code=1)


async def _get_model_info_async(host: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch model information from Ollama server."""
    async with OllamaClient(host=host) as client:
        model_data = await client.show_model(model)
        capabilities = await get_capabilities(client, model)
        return model_data, {
            "supports_vision": capabilities.supports_vision,
            "max_context": capabilities.max_context,
            "families": capabilities.families,
            "parameter_size": capabilities.parameter_size,
            "quantization": capabilities.quantization,
        }