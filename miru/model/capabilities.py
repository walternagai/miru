"""Model capability detection module."""

from dataclasses import dataclass

from miru.ollama.client import OllamaClient


@dataclass
class ModelCapabilities:
    """Model capabilities metadata."""

    supports_vision: bool
    max_context: int
    families: list[str]
    parameter_size: str
    quantization: str


def _extract_num_ctx(parameters: str) -> int | None:
    """
    Extract num_ctx value from parameters string.

    Parameters format: "num_ctx\\t4096\\nnum_batch\\t512\\n..."

    Args:
        parameters: Raw parameters string from /api/show

    Returns:
        num_ctx value if found, None otherwise
    """
    for line in parameters.split("\n"):
        line = line.strip()
        if line.startswith("num_ctx"):
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    pass
    return None


async def get_capabilities(client: OllamaClient, model: str) -> ModelCapabilities:
    """
    Get capabilities for a given model.

    Args:
        client: OllamaClient instance
        model: Model name (e.g., "llava:latest")

    Returns:
        ModelCapabilities with detected features

    Example:
        async with OllamaClient(host) as client:
            caps = await get_capabilities(client, "llava:latest")
            print(caps.supports_vision)  # True
    """
    data = await client.show_model(model)

    details = data.get("details", {})
    families: list[str] = details.get("families", [])
    parameter_size = details.get("parameter_size", "unknown")
    quantization = details.get("quantization_level", "unknown")

    supports_vision = "clip" in families

    model_info = data.get("modelinfo", {})
    parameters = data.get("parameters", "")

    max_context: int | None = None

    if "llm.context_length" in model_info:
        max_context = int(model_info["llm.context_length"])
    elif parameters:
        extracted = _extract_num_ctx(parameters)
        if extracted:
            max_context = extracted

    if max_context is None:
        max_context = 2048

    return ModelCapabilities(
        supports_vision=supports_vision,
        max_context=max_context,
        families=families,
        parameter_size=parameter_size,
        quantization=quantization,
    )