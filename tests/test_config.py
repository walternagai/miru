"""Tests for miru/config.py."""

import os

import pytest

from miru.config import DEFAULT_HOST, get_host


class TestGetHost:
    """Tests for get_host function."""

    def test_get_host_default_no_env_no_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return default host when no env var and no override."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        result = get_host()
        assert result == DEFAULT_HOST
        assert result == "http://localhost:11434"

    def test_get_host_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return host from OLLAMA_HOST env var."""
        monkeypatch.setenv("OLLAMA_HOST", "http://192.168.1.10:11434")
        result = get_host()
        assert result == "http://192.168.1.10:11434"

    def test_get_host_override_wins_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Override parameter should have highest precedence."""
        monkeypatch.setenv("OLLAMA_HOST", "http://from-env:11434")
        result = get_host(override="http://from-override:11434")
        assert result == "http://from-override:11434"

    def test_get_host_trailing_slash_removed(self) -> None:
        """Should strip trailing slash from host."""
        result = get_host(override="http://localhost:11434/")
        assert result == "http://localhost:11434"
        assert not result.endswith("/")

    def test_get_host_trailing_slash_with_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should only strip trailing slash, not add or remove path."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        result = get_host(override="http://custom:11434/")
        assert result == "http://custom:11434"

    def test_get_host_override_none_uses_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Override=None should fall back to env var."""
        monkeypatch.setenv("OLLAMA_HOST", "http://from-env:11434")
        result = get_host(override=None)
        assert result == "http://from-env:11434"

    def test_get_host_empty_override_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string override should not override env var."""
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        result = get_host(override="")
        assert result == DEFAULT_HOST

class TestConfigResolvers:
    def test_resolve_host_with_override(self) -> None:
        from miru.core.config import resolve_host

        assert resolve_host("http://override:11434") == "http://override:11434"

    def test_resolve_host_from_env(self, monkeypatch) -> None:
        from miru.core.config import resolve_host

        monkeypatch.setenv("OLLAMA_HOST", "http://from-env:11434")
        assert resolve_host(None) == "http://from-env:11434"

    def test_resolve_tool_mode(self) -> None:
        from miru.core.config import resolve_tool_mode

        assert resolve_tool_mode("manual") == "manual"

    def test_resolve_sandbox_dir_override(self) -> None:
        from miru.core.config import resolve_sandbox_dir

        assert resolve_sandbox_dir("/tmp/x") == "/tmp/x"

    def test_config_to_dict_from_dict(self) -> None:
        from miru.core.config import Config

        c = Config(default_host="http://x", default_model="m")
        d = c.to_dict()
        assert d["default_host"] == "http://x"
        c2 = Config.from_dict(d)
        assert c2.default_host == "http://x"

    def test_get_config_value_unknown(self) -> None:
        from miru.core.config import get_config_value

        assert get_config_value("chave_que_nao_existe") is None


class TestReloadConfig:
    def test_reload_returns_config(self, tmp_path, monkeypatch) -> None:
        import miru.core.config as cfg_mod

        monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / "config.toml")
        config = cfg_mod.reload_config()
        assert config is not None
