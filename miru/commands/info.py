"""miru info command - show model information.

Refactored with i18n support.
"""

import asyncio
from typing import Any

import typer

from miru.alias import resolve_alias
from miru.cli_options import Host, Format, Quiet, Model
from miru.core.config import resolve_host
from miru.core.errors import ModelNotFoundError, ConnectionError as MiruConnectionError
from miru.core.i18n import t
from miru.model.capabilities import get_capabilities
from miru.ollama.client import OllamaClient
from miru.renderer import render_error, render_model_info, render_model_info_json


def info(
    model: Model,
    host: Host = None,
    format: Format = "text",
    quiet: Quiet = False,
) -> None:
    """
    Show detailed information about a model.

    Examples:
        miru info gemma3:latest
        miru info llava --format json
    """
    model = resolve_alias(model)
    ollama_host = resolve_host(host)

    try:
        model_data, capabilities_data = asyncio.run(
            _get_model_info_async(ollama_host, model)
        )

        if format == "json":
            render_model_info_json(model_data, capabilities_data, quiet=quiet)
        else:
            render_model_info(model, model_data, capabilities_data, quiet=quiet)

    except Exception:
        # Try to get available models for suggestion
        available = []
        try:
            async def get_models():
                async with OllamaClient(host=ollama_host) as client:
                    return await client.list_models()
            models = asyncio.run(get_models())
            available = [m.get("name", "") for m in models[:5]]
        except Exception:
            pass
        
        error = ModelNotFoundError(model, available)
        render_error(error.message, error.suggestion)
        raise typer.Exit(code=1)


async def _get_model_info_async(host: str, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch model information from Ollama server."""
    async with OllamaClient(host=host) as client:
        model_data = await client.show_model(model)
        capabilities = await get_capabilities(client, model)
    return model_data, {
        "supports_vision": capabilities.supports_vision,
        "capabilities": capabilities.capabilities,
        "max_context": capabilities.max_context,
        "families": capabilities.families,
        "parameter_size": capabilities.parameter_size,
        "quantization": capabilities.quantization,
    }