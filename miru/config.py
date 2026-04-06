"""Configuration module for resolving Ollama host."""

import os

DEFAULT_HOST = "http://localhost:11434"


def get_host(override: str | None = None) -> str:
    """
    Resolve Ollama host with precedence chain.

    Precedence (highest to lowest):
    1. Explicit override parameter
    2. OLLAMA_HOST environment variable
    3. Default http://localhost:11434

    Args:
        override: Explicit host URL to use

    Returns:
        Base URL without trailing slash

    Examples:
        >>> get_host()
        'http://localhost:11434'
        >>> get_host(override='http://custom:11434/')
        'http://custom:11434'
    """
    host = override or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
    return host.rstrip("/")
