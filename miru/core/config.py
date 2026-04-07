"""Unified configuration management for miru CLI.

Consolidates all configuration logic into a single module with:
- File-based config (TOML)
- Environment variables
- Profiles
- Precedence chain
"""

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
    """Configuration settings for miru CLI.
    
    Attributes:
        default_host: Ollama server URL
        default_model: Default model for commands
        default_timeout: Request timeout in seconds
        language: UI language (pt_BR, en_US, es_ES)
        history_enabled: Whether to save prompt history
        history_max_entries: Maximum history entries
        verbose: Enable verbose output
        tavily_api_key: Tavily API key for web search
        enable_tools: Enable all tools by default
        enable_tavily: Enable Tavily web search
        tool_mode: Tool execution mode (manual, auto, auto_safe)
        sandbox_dir: Sandbox directory for file tools
        profiles: Named configuration profiles
        current_profile: Active profile name
    """
    
    default_host: str = "http://localhost:11434"
    default_model: str | None = None
    default_timeout: float = 30.0
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    default_top_p: float | None = None
    default_top_k: int | None = None
    default_seed: int | None = None
    
    language: str = "en_US"
    
    history_enabled: bool = True
    history_max_entries: int = 1000
    verbose: bool = False
    
    tavily_api_key: str | None = None
    enable_tools: bool = False
    enable_tavily: bool = False
    tool_mode: str = "auto_safe"
    sandbox_dir: str | None = None
    
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_profile: str | None = None
    
    def get_host(self) -> str:
        """Get host with profile override."""
        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile].get("host", self.default_host)
        return self.default_host
    
    def get_model(self) -> str | None:
        """Get default model with profile override."""
        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile].get("default_model", self.default_model)
        return self.default_model
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        data: dict[str, Any] = {
            "default_host": self.default_host,
            "default_model": self.default_model,
            "default_timeout": self.default_timeout,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "default_top_p": self.default_top_p,
            "default_top_k": self.default_top_k,
            "default_seed": self.default_seed,
            "language": self.language,
            "history_enabled": self.history_enabled,
            "history_max_entries": self.history_max_entries,
            "verbose": self.verbose,
            "tavily_api_key": self.tavily_api_key,
            "enable_tools": self.enable_tools,
            "enable_tavily": self.enable_tavily,
            "tool_mode": self.tool_mode,
            "sandbox_dir": self.sandbox_dir,
            "profiles": self.profiles,
            "current_profile": self.current_profile,
        }
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        config = cls()
        for key, value in data.items():
            if key == "profiles":
                config.profiles = value
            elif hasattr(config, key):
                setattr(config, key, value)
        return config


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "templates").mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "logs").mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load configuration from TOML file.
    
    Returns:
        Config object with loaded or default values
    """
    ensure_config_dir()
    
    if not CONFIG_FILE.exists():
        return Config()
    
    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        return Config.from_dict(data)
    except Exception:
        return Config()


def save_config(config: Config) -> None:
    """Save configuration to TOML file.
    
    Args:
        config: Config object to save
    """
    if tomli_w is None:
        print("Warning: tomli_w not installed. Cannot save config.")
        return
    
    ensure_config_dir()
    
    data = config.to_dict()
    
    data = {
        k: v
        for k, v in data.items()
        if v is not None and v != Config.__dataclass_fields__[k].default
    }
    
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def get_config_value(key: str) -> Any:
    """Get a single config value with precedence chain.
    
    Precedence:
    1. Environment variable (MIRU_*)
    2. Config file
    3. Default
    
    Args:
        key: Configuration key name
        
    Returns:
        Configuration value
    """
    import os
    
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
    
    Precedence:
    1. CLI override
    2. Environment variable OLLAMA_HOST
    3. Environment variable MIRU_DEFAULT_HOST
    4. Config file
    5. Default
    
    Args:
        cli_override: CLI argument for host
        
    Returns:
        Resolved host URL
    """
    import os
    
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
    
    Args:
        cli_override: CLI argument for model
        
    Returns:
        Resolved model name or None
    """
    if cli_override:
        return cli_override
    
    return get_config_value("default_model")


def resolve_enable_tools(cli_override: bool | None = None) -> bool:
    """Resolve enable_tools with precedence.
    
    Args:
        cli_override: CLI argument
        
    Returns:
        Boolean value
    """
    if cli_override is not None:
        return cli_override
    
    return bool(get_config_value("enable_tools"))


def resolve_enable_tavily(cli_override: bool | None = None) -> bool:
    """Resolve enable_tavily with precedence.
    
    Args:
        cli_override: CLI argument
        
    Returns:
        Boolean value
    """
    if cli_override is not None:
        return cli_override
    
    return bool(get_config_value("enable_tavily"))


def resolve_tool_mode(cli_override: str | None = None) -> str:
    """Resolve tool_mode with precedence.
    
    Args:
        cli_override: CLI argument
        
    Returns:
        Tool mode string
    """
    if cli_override:
        return cli_override
    
    mode = get_config_value("tool_mode")
    if mode and mode in ("manual", "auto", "auto_safe"):
        return str(mode)
    
    return "auto_safe"


def resolve_sandbox_dir(cli_override: str | None = None) -> str | None:
    """Resolve sandbox_dir with precedence.
    
    Args:
        cli_override: CLI argument
        
    Returns:
        Sandbox directory path or None
    """
    if cli_override:
        return cli_override
    
    return get_config_value("sandbox_dir")


_config_instance: Config | None = None


def get_config() -> Config:
    """Get cached config instance.
    
    Loads config once and caches it for subsequent calls.
    Call reload_config() to force reload.
    
    Returns:
        Config object
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


def reload_config() -> Config:
    """Force reload configuration from disk.
    
    Returns:
        Freshly loaded Config object
    """
    global _config_instance
    _config_instance = load_config()
    return _config_instance