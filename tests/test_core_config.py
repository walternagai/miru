"""Tests for core.config module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from miru.core.config import (
    Config,
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
    ensure_config_dir,
    CONFIG_DIR,
)


class TestConfig:
    """Test Config class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        assert config.default_host == "http://localhost:11434"
        assert config.default_model is None
        assert config.default_timeout == 30.0
        assert config.language == "en_US"
        assert config.history_enabled is True
        assert config.history_max_entries == 1000

    def test_get_host(self):
        """Test get_host method."""
        config = Config(default_host="http://custom:8080")
        assert config.get_host() == "http://custom:8080"

    def test_get_host_with_profile(self):
        """Test get_host with profile override."""
        config = Config(
            default_host="http://localhost:11434",
            profiles={"work": {"host": "http://work:8080"}},
            current_profile="work"
        )
        assert config.get_host() == "http://work:8080"

    def test_get_model(self):
        """Test get_model method."""
        config = Config(default_model="gemma3:latest")
        assert config.get_model() == "gemma3:latest"

    def test_get_model_with_profile(self):
        """Test get_model with profile override."""
        config = Config(
            default_model="gemma3:latest",
            profiles={"work": {"default_model": "qwen2.5:7b"}},
            current_profile="work"
        )
        assert config.get_model() == "qwen2.5:7b"

    def test_to_dict(self):
        """Test config to dictionary conversion."""
        config = Config(
            default_host="http://localhost:11434",
            default_model="gemma3",
            language="pt_BR"
        )
        data = config.to_dict()
        assert data["default_host"] == "http://localhost:11434"
        assert data["default_model"] == "gemma3"
        assert data["language"] == "pt_BR"

    def test_from_dict(self):
        """Test config from dictionary."""
        data = {
            "default_host": "http://custom:8080",
            "default_model": "qwen2",
            "language": "es_ES"
        }
        config = Config.from_dict(data)
        assert config.default_host == "http://custom:8080"
        assert config.default_model == "qwen2"
        assert config.language == "es_ES"


class TestLoadSaveConfig:
    """Test load and save configuration."""

    def test_load_config_missing(self, tmp_path):
        """Test loading config when file doesn't exist."""
        with patch("miru.core.config.CONFIG_FILE", tmp_path / "missing.toml"):
            config = load_config()
            # Returns default config
            assert config.default_host == "http://localhost:11434"

    def test_save_and_load_config(self, tmp_path):
        """Test saving and loading configuration."""
        config_file = tmp_path / "config.toml"
        with patch("miru.core.config.CONFIG_FILE", config_file):
            config = Config(
                default_host="http://custom:8080",
                default_model="test-model",
                language="pt_BR"
            )
            save_config(config)

            # Check file was created
            assert config_file.exists()

            # Load and verify
            loaded = load_config()
            assert loaded.default_host == "http://custom:8080"
            assert loaded.default_model == "test-model"
            assert loaded.language == "pt_BR"


class TestResolveFunctions:
    """Test resolve functions."""

    def test_resolve_host_cli_override(self):
        """Test resolve_host with CLI override."""
        result = resolve_host("http://custom:8080")
        assert result == "http://custom:8080"

    def test_resolve_host_env_ollama(self, monkeypatch):
        """Test resolve_host with OLLAMA_HOST env."""
        monkeypatch.setenv("OLLAMA_HOST", "http://ollama:11434")
        result = resolve_host()
        assert result == "http://ollama:11434"

    def test_resolve_host_default(self, monkeypatch):
        """Test resolve_host default value."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("MIRU_DEFAULT_HOST", raising=False)
        result = resolve_host()
        assert result == "http://localhost:11434"

    def test_resolve_model_cli_override(self):
        """Test resolve_model with CLI override."""
        result = resolve_model("gemma3")
        assert result == "gemma3"

    def test_resolve_model_default(self):
        """Test resolve_model default value."""
        result = resolve_model()
        assert result is None or isinstance(result, str)

    def test_resolve_enable_tools(self):
        """Test resolve_enable_tools."""
        # Default is False
        result = resolve_enable_tools()
        assert isinstance(result, bool)

    def test_resolve_enable_tavily(self):
        """Test resolve_enable_tavily."""
        result = resolve_enable_tavily()
        assert isinstance(result, bool)

    def test_resolve_tool_mode_default(self):
        """Test resolve_tool_mode default."""
        result = resolve_tool_mode()
        assert result == "auto_safe"

    def test_resolve_tool_mode_override(self):
        """Test resolve_tool_mode with override."""
        result = resolve_tool_mode("manual")
        assert result == "manual"

    def test_resolve_tool_mode_invalid(self):
        """Test resolve_tool_mode with invalid value."""
        # Invalid values are passed through (validation happens elsewhere)
        result = resolve_tool_mode("invalid")
        assert result == "invalid"

    def test_resolve_sandbox_dir(self):
        """Test resolve_sandbox_dir."""
        result = resolve_sandbox_dir()
        assert result is None or isinstance(result, str)


class TestGetConfigValue:
    """Test get_config_value function."""

    def test_get_config_value_missing(self):
        """Test getting missing config value."""
        result = get_config_value("nonexistent_key")
        assert result is None

    def test_get_config_value_from_env(self, monkeypatch):
        """Test getting config value from environment."""
        monkeypatch.setenv("MIRU_DEFAULT_HOST", "http://env:8080")
        result = get_config_value("default_host")
        assert result == "http://env:8080"

    def test_get_config_value_bool_true(self, monkeypatch):
        """Test getting boolean config value (true)."""
        monkeypatch.setenv("MIRU_HISTORY_ENABLED", "true")
        result = get_config_value("history_enabled")
        assert result is True

    def test_get_config_value_bool_false(self, monkeypatch):
        """Test getting boolean config value (false)."""
        monkeypatch.setenv("MIRU_HISTORY_ENABLED", "false")
        result = get_config_value("history_enabled")
        assert result is False

    def test_get_config_value_int(self, monkeypatch):
        """Test getting integer config value."""
        monkeypatch.setenv("MIRU_HISTORY_MAX_ENTRIES", "500")
        result = get_config_value("history_max_entries")
        assert result == 500


class TestConfigInstance:
    """Test get_config and reload_config functions."""

    def test_get_config_caches(self):
        """Test that get_config caches result."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_config(self):
        """Test reload_config creates new instance."""
        config1 = get_config()
        config2 = reload_config()
        assert config1 is not config2


class TestEnsureConfigDir:
    """Test ensure_config_dir function."""

    def test_ensure_config_dir(self, tmp_path):
        """Test that config directory is created."""
        with patch("miru.core.config.CONFIG_DIR", tmp_path / ".miru"):
            ensure_config_dir()
            assert (tmp_path / ".miru").exists()
            assert (tmp_path / ".miru" / "templates").exists()
            assert (tmp_path / ".miru" / "logs").exists()