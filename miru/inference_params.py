"""Shared inference parameters for run, chat, and compare commands."""

KEY_MAP = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "max_tokens": "num_predict",
    "seed": "seed",
    "repeat_penalty": "repeat_penalty",
    "ctx": "num_ctx",
}


def build_options(
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    max_tokens: int | None,
    seed: int | None,
    repeat_penalty: float | None,
    ctx: int | None,
) -> dict[str, float | int] | None:
    """
    Build options dict for Ollama API from inference parameters.

    Returns dict with only non-None fields, translating max_tokens to num_predict.
    Returns None if all parameters are None (empty options should be omitted).

    Args:
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling probability
        top_k: Top-k sampling
        max_tokens: Max tokens to generate (mapped to num_predict)
        seed: Random seed for reproducibility
        repeat_penalty: Repetition penalty
        ctx: Context window size (mapped to num_ctx)

    Returns:
        Dict with API-compatible field names, or None if all params are None

    Example:
        >>> build_options(temperature=0.7, top_p=None, top_k=None,
        ...               max_tokens=200, seed=None, repeat_penalty=None, ctx=None)
        {'temperature': 0.7, 'num_predict': 200}
    """
    params = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "max_tokens": max_tokens,
        "seed": seed,
        "repeat_penalty": repeat_penalty,
        "ctx": ctx,
    }

    options: dict[str, float | int] = {}
    for param_name, value in params.items():
        if value is not None:
            api_key = KEY_MAP[param_name]
            options[api_key] = value

    return options if options else None