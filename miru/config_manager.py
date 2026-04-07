"""Compatibility module - delegates to core.config.

This module is kept for backward compatibility.
New code should use miru.core.config directly.
"""

# Re-export everything from core.config for backward compatibility
from miru.core.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    HISTORY_FILE,
    TEMPLATE_DIR,
    ALIAS_FILE,
    LOG_DIR,
    Config,
    ensure_config_dir,
    load_config,
    save_config,
    get_config_value,
    resolve_host,
    resolve_model,
    resolve_enable_tools,
    resolve_enable_tavily,
    resolve_tool_mode,
    resolve_sandbox_dir,
    get_config,
    reload_config,
)

# Compatibility alias
HistoryFile = HISTORY_FILE
TemplateDir = TEMPLATE_DIR
AliasFile = ALIAS_FILE
LogDir = LOG_DIR

__all__ = [
    "CONFIG_DIR",
    "CONFIG_FILE",
    "HISTORY_FILE",
    "TEMPLATE_DIR",
    "ALIAS_FILE",
    "LOG_DIR",
    "Config",
    "ensure_config_dir",
    "load_config",
    "save_config",
    "get_config_value",
    "resolve_host",
    "resolve_model",
    "resolve_enable_tools",
    "resolve_enable_tavily",
    "resolve_tool_mode",
    "resolve_sandbox_dir",
    "get_config",
    "reload_config",
    "HistoryFile",
    "TemplateDir",
    "AliasFile",
    "LogDir",
]