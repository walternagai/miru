"""Configuration management with persistent storage."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib

try:
    import tomli_w
except ImportError:
    tomli_w = None

CONFIG_DIR = Path.home() / ".miru"
CONFIG_FILE = CONFIG_DIR / "config.toml"
HISTORY_FILE = CONFIG_DIR / "history.jsonl"
TEMPLATE_DIR = CONFIG_DIR / "templates"
ALIAS_FILE = CONFIG_DIR / "aliases.toml"
LOG_DIR = CONFIG_DIR / "logs"


@dataclass
class Config:
    """Configuration settings for miru CLI."""

    default_host: str = "http://localhost:11434"
    default_model: str | None = None
    default_timeout: float = 30.0
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    default_top_p: float | None = None
    default_top_k: int | None = None
    default_seed: int | None = None
    history_enabled: bool = True
    history_max_entries: int = 1000
    verbose: bool = False
    tavily_api_key: str | None = None
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_profile: str | None = None

    def get_host(self) -> str:
        """Get host with profile override if applicable."""
        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile].get("host", self.default_host)
        return self.default_host

    def get_model(self) -> str | None:
        """Get default model with profile override if applicable."""
        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile].get("default_model", self.default_model)
        return self.default_model


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load configuration from TOML file."""
    ensure_config_dir()

    if not CONFIG_FILE.exists():
        return Config()

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        config = Config()
        for key, value in data.items():
            if key == "profiles":
                config.profiles = value
            elif hasattr(config, key):
                setattr(config, key, value)

        return config
    except Exception:
        return Config()


def save_config(config: Config) -> None:
    """Save configuration to TOML file."""
    if tomli_w is None:
        print("Warning: tomli_w not installed. Cannot save config.")
        return

    ensure_config_dir()

    data: dict[str, Any] = {
        "default_host": config.default_host,
        "default_model": config.default_model,
        "default_timeout": config.default_timeout,
        "default_temperature": config.default_temperature,
        "default_max_tokens": config.default_max_tokens,
        "default_top_p": config.default_top_p,
        "default_top_k": config.default_top_k,
        "default_seed": config.default_seed,
        "history_enabled": config.history_enabled,
        "history_max_entries": config.history_max_entries,
        "verbose": config.verbose,
        "tavily_api_key": config.tavily_api_key,
        "profiles": config.profiles,
        "current_profile": config.current_profile,
    }

    data = {
        k: v
        for k, v in data.items()
        if v is not None and v != Config.__dataclass_fields__[k].default
    }

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def get_config_value(key: str) -> Any:
    """Get a single config value.

    Precedence:
    1. Environment variable (MIRU_*)
    2. Config file
    3. Default
    """
    env_key = f"MIRU_{key.upper()}"
    env_value = os.environ.get(env_key)

    if env_value is not None:
        if env_value.lower() in ("true", "1", "yes"):
            return True
        if env_value.lower() in ("false", "0", "no"):
            return False
        try:
            return float(env_value) if "." in env_value else int(env_value)
        except ValueError:
            return env_value

    config = load_config()
    return getattr(config, key, None)


def resolve_host(cli_override: str | None = None) -> str:
    """Resolve host with full precedence chain.

    1. CLI override
    2. Environment variable OLLAMA_HOST
    3. Environment variable MIRU_DEFAULT_HOST
    4. Config file
    5. Default
    """
    if cli_override:
        return cli_override.rstrip("/")

    ollama_host = os.environ.get("OLLAMA_HOST")
    if ollama_host:
        return ollama_host.rstrip("/")

    config_host = get_config_value("default_host")
    if config_host:
        return str(config_host).rstrip("/")

    return "http://localhost:11434"


def resolve_model(cli_override: str | None = None) -> str | None:
    """Resolve default model with precedence.

    1. CLI override
    2. Config file
    """
    if cli_override:
        return cli_override

    return get_config_value("default_model")
