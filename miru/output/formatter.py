"""Formatter module for data serialization (stdlib only, no Rich)."""

import json
from typing import Any


def to_json(data: dict | list, indent: int = 2) -> str:
    """
    Serialize to JSON with indentation and ensure_ascii=False.

    Args:
        data: Data to serialize
        indent: Indentation level (default 2)

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def print_json(data: dict | list) -> None:
    """
    Print JSON serialized data to stdout.

    Args:
        data: Data to serialize and print
    """
    print(to_json(data))


def models_to_json(models: list[dict]) -> list[dict]:
    """
    Add 'size_human' field to each model.

    Args:
        models: List of model dicts

    Returns:
        New list with size_human field (doesn't modify original)
    """
    result = []
    for model in models:
        model_copy = dict(model)
        size = model.get("size", 0)
        model_copy["size_human"] = _format_size(size)
        result.append(model_copy)
    return result


def result_to_json(result) -> dict:
    """
    Convert ModelResult to JSON-serializable dict.

    Args:
        result: ModelResult object

    Returns:
        Dict with model, prompt, response, metrics, error fields
    """
    if result.error is not None:
        return {
            "model": result.model,
            "prompt": result.prompt,
            "response": result.response,
            "metrics": None,
            "error": result.error,
        }

    return {
        "model": result.model,
        "prompt": result.prompt,
        "response": result.response,
        "metrics": {
            "eval_count": result.eval_count,
            "eval_duration_ns": result.eval_duration_ns,
            "total_duration_ns": result.total_duration_ns,
            "tokens_per_second": round(result.tokens_per_second, 1),
        },
        "error": None,
    }


def print_plain(text: str) -> None:
    """
    Write plain text to stdout without Rich decoration.

    Args:
        text: Text to print
    """
    print(text)


def _format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable format (GB/MB/KB).

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable string (e.g., "5.0 GB", "500 MB")
    """
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"