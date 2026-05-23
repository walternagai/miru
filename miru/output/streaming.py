"""Output streaming utilities (backward compatible module)."""

import json
from collections.abc import AsyncIterator
from typing import Any

from miru.latex_unicode import latex_to_unicode
from miru.output.renderer import format_metrics


async def render_stream(
    chunks: AsyncIterator[dict[str, Any]],
    quiet: bool = False,
    output_format: str = "text",
) -> dict[str, Any] | None:
    """
    Render streaming tokens from generate() or chat().

    In text mode: prints tokens as they arrive
    In quiet mode: suppresses all output
    In JSON mode: collects all tokens and prints final JSON

    Args:
        chunks: Async iterator of response chunks
        quiet: If True, suppress output (only return final chunk)
        output_format: "text" or "json"

    Returns:
        Final chunk with metrics, or None
    """
    collected_response = []
    final_chunk = None
    model = None
    prompt = None

    async for chunk in chunks:
        if output_format == "json":
            if "response" in chunk:
                collected_response.append(chunk.get("response", ""))
            if "message" in chunk:
                collected_response.append(chunk.get("message", {}).get("content", ""))

        if not quiet and output_format == "text":
            if "response" in chunk:
                text = chunk.get("response", "")
                if text:
                    print(latex_to_unicode(text), end="", flush=True)
            elif "message" in chunk:
                text = chunk.get("message", {}).get("content", "")
                if text:
                    print(latex_to_unicode(text), end="", flush=True)

        if chunk.get("done"):
            final_chunk = chunk
            if "model" in chunk:
                model = chunk.get("model")
            if "context" in chunk:
                prompt = chunk.get("context")

    if not quiet and output_format == "text":
        print()

    if output_format == "json" and final_chunk:
        response_text = "".join(collected_response)
        output_data = _build_json_output(final_chunk, response_text, model, prompt)
        print(json.dumps(output_data, indent=2))

    return final_chunk


def _calc_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Calculate derived metrics from chunk data using shared logic."""
    eval_count = metrics.get("eval_count", 0)
    total_duration_ns = metrics.get("total_duration", 0)
    eval_duration_ns = metrics.get("eval_duration", 0)

    total_seconds = total_duration_ns / 1e9 if total_duration_ns else 0.0

    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
    elif total_duration_ns and total_duration_ns > 0:
        tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
    else:
        tokens_per_second = 0.0

    return {
        "eval_count": eval_count,
        "eval_duration_ns": eval_duration_ns,
        "total_duration_ns": total_duration_ns,
        "tokens_per_second": round(tokens_per_second, 1),
    }


def render_json_output(
    model: str,
    prompt: str,
    response: str,
    metrics: dict[str, Any] | None,
) -> None:
    """Render final JSON output for run command."""
    output: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "response": response,
    }

    if metrics:
        output["metrics"] = _calc_metrics(metrics)

    print(json.dumps(output, indent=2))


async def collect_stream(
    chunks: AsyncIterator[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None, str | None]:
    """
    Collect all tokens from stream without rendering.

    Args:
        chunks: Async iterator of response chunks

    Returns:
        Tuple of (collected_text, final_chunk, model_name)
    """
    collected = []
    final_chunk = None
    model_name = None

    async for chunk in chunks:
        if "response" in chunk:
            collected.append(chunk.get("response", ""))
        if "message" in chunk:
            collected.append(chunk.get("message", {}).get("content", ""))

        if chunk.get("done"):
            final_chunk = chunk
            if "model" in chunk:
                model_name = chunk.get("model")

    return "".join(collected), final_chunk, model_name
