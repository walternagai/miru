"""Output streaming utilities (backward compatible module)."""

import json
from collections.abc import AsyncIterator
from typing import Any

from miru.latex_unicode import latex_to_unicode


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


def render_metrics(metrics: dict[str, Any], compact: bool = False) -> None:
    """
    Render inference metrics.

    Args:
        metrics: Dict with eval_count, eval_duration, total_duration
        compact: If True, use compact format [47 tok · 20.4 tok/s]
                 If False, use full format ✓ 47 tokens · 2.3s · 20.4 tok/s
    """
    eval_count = metrics.get("eval_count", 0)
    total_duration_ns = metrics.get("total_duration", 0)
    eval_duration_ns = metrics.get("eval_duration", 0)

    total_seconds = total_duration_ns / 1e9 if total_duration_ns else 0.0

    # Calculate tokens per second, preferring eval_duration
    # Fallback to total_duration if eval_duration is not available
    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
    elif total_duration_ns and total_duration_ns > 0:
        tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
    else:
        tokens_per_second = 0.0

    if compact:
        if tokens_per_second > 0:
            print(f"[{eval_count} tok · {tokens_per_second:.1f} tok/s]")
        else:
            print(f"[{eval_count} tok]")
    else:
        if tokens_per_second > 0:
            print(f"✓ {eval_count} tokens · {total_seconds:.1f}s · {tokens_per_second:.1f} tok/s")
        else:
            print(f"✓ {eval_count} tokens · {total_seconds:.1f}s")


def render_json_output(
    model: str,
    prompt: str,
    response: str,
    metrics: dict[str, Any] | None,
) -> None:
    """
    Render final JSON output for run command.

    Args:
        model: Model name
        prompt: Input prompt
        response: Generated response
        metrics: Metrics dict from final chunk
    """
    output: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "response": response,
    }

    if metrics:
        eval_count = metrics.get("eval_count", 0)
        total_duration_ns = metrics.get("total_duration", 0)
        eval_duration_ns = metrics.get("eval_duration", 0)

        # Calculate tokens per second with fallback
        if eval_duration_ns and eval_duration_ns > 0:
            eval_seconds = eval_duration_ns / 1e9
            tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
        elif total_duration_ns and total_duration_ns > 0:
            total_seconds = total_duration_ns / 1e9
            tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
        else:
            tokens_per_second = 0.0

        output["metrics"] = {
            "eval_count": eval_count,
            "eval_duration_ns": eval_duration_ns,
            "total_duration_ns": total_duration_ns,
            "tokens_per_second": round(tokens_per_second, 1),
        }

    print(json.dumps(output, indent=2))


def _build_json_output(
    final_chunk: dict[str, Any],
    response: str,
    model: str | None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """
    Build JSON output structure from final chunk.

    Args:
        final_chunk: Final done chunk from generate/chat
        response: Collected response text
        model: Model name
        prompt: Original prompt (for generate)

    Returns:
        Dict with model, response, and metrics
    """
    eval_count = final_chunk.get("eval_count", 0)
    total_duration_ns = final_chunk.get("total_duration", 0)
    eval_duration_ns = final_chunk.get("eval_duration", 0)

    # Calculate tokens per second with fallback
    if eval_duration_ns and eval_duration_ns > 0:
        eval_seconds = eval_duration_ns / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
    elif total_duration_ns and total_duration_ns > 0:
        total_seconds = total_duration_ns / 1e9
        tokens_per_second = eval_count / total_seconds if total_seconds > 0 else 0.0
    else:
        tokens_per_second = 0.0

    result: dict[str, Any] = {
        "model": model or final_chunk.get("model", "unknown"),
        "response": response,
        "metrics": {
            "eval_count": eval_count,
            "eval_duration_ns": eval_duration_ns,
            "total_duration_ns": total_duration_ns,
            "tokens_per_second": round(tokens_per_second, 1),
        },
    }

    if prompt is not None:
        result["prompt"] = prompt

    return result


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
