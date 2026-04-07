"""Model capability detection module."""

from dataclasses import dataclass

from miru.ollama.client import OllamaClient


@dataclass
class ModelCapabilities:
    """Model capabilities metadata."""

    supports_vision: bool
    capabilities: list[str]
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
    families: list[str] = details.get("families") or []
    parameter_size = details.get("parameter_size", "unknown")
    quantization = details.get("quantization_level", "unknown")

    # Extract capabilities from API response
    raw_capabilities = data.get("capabilities") or []
    
    # Check for vision support:
    # 1. "clip" in families (local models)
    # 2. "vision" in capabilities (cloud/remote models)
    supports_vision = "clip" in families or "vision" in raw_capabilities

    model_info = data.get("modelinfo", data.get("model_info", {}))
    parameters = data.get("parameters", "")

    max_context: int | None = None

    # Try different context length field patterns:
    # - llm.context_length (llama-based models)
    # - gemma3.context_length (gemma models)
    # - <arch>.context_length (architecture-specific)
    for key, value in model_info.items():
        if "context_length" in key:
            try:
                max_context = int(value)
                break
            except (ValueError, TypeError):
                pass

    # Fallback to parameters string
    if max_context is None and parameters:
        extracted = _extract_num_ctx(parameters)
        if extracted:
            max_context = extracted

    if max_context is None:
        max_context = 2048

    return ModelCapabilities(
        supports_vision=supports_vision,
        capabilities=raw_capabilities,
        max_context=max_context,
        families=families,
        parameter_size=parameter_size,
        quantization=quantization,
    )
