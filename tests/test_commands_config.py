"""Tests for miru/commands/config_cmd.py — config set/get/list/reset via CLI."""

from unittest.mock import patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _config_with_tmpfile(tmp_path, monkeypatch):
    """Point config save/load at a tmp path and provide a real Config."""
    import miru.commands.config_cmd as cfg_mod
    from miru.core.config import Config

    cfg = Config()
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr(cfg_mod, "load_config", lambda: cfg)
    monkeypatch.setattr(cfg_mod, "save_config", lambda c: None)
    return cfg


class TestConfigSet:
    def test_set_valid_string(self) -> None:
        result = runner.invoke(app, ["config", "set", "default_host", "http://x:11434"])
        assert result.exit_code == 0

    def test_set_unknown_key_exits(self) -> None:
        result = runner.invoke(app, ["config", "set", "not_a_key", "v"])
        assert result.exit_code == 1

    def test_set_boolean_true(self, _config_with_tmpfile) -> None:
        result = runner.invoke(app, ["config", "set", "history_enabled", "true"])
        assert result.exit_code == 0
        assert _config_with_tmpfile.history_enabled is True

    def test_set_boolean_invalid(self) -> None:
        result = runner.invoke(app, ["config", "set", "history_enabled", "maybe"])
        assert result.exit_code == 1

    def test_set_float(self, _config_with_tmpfile) -> None:
        result = runner.invoke(app, ["config", "set", "default_temperature", "0.5"])
        assert result.exit_code == 0
        assert _config_with_tmpfile.default_temperature == 0.5

    def test_set_float_invalid(self) -> None:
        result = runner.invoke(app, ["config", "set", "default_temperature", "abc"])
        assert result.exit_code == 1

    def test_set_int(self, _config_with_tmpfile) -> None:
        result = runner.invoke(app, ["config", "set", "history_max_entries", "500"])
        assert result.exit_code == 0
        assert _config_with_tmpfile.history_max_entries == 500

    def test_set_int_invalid(self) -> None:
        result = runner.invoke(app, ["config", "set", "history_max_entries", "abc"])
        assert result.exit_code == 1

    def test_set_tool_mode_valid(self) -> None:
        result = runner.invoke(app, ["config", "set", "tool_mode", "manual"])
        assert result.exit_code == 0

    def test_set_tool_mode_invalid(self) -> None:
        result = runner.invoke(app, ["config", "set", "tool_mode", "bogus"])
        assert result.exit_code == 1

    def test_set_tavily_key_warning(self) -> None:
        result = runner.invoke(app, ["config", "set", "tavily_api_key", "bad-key"])
        assert result.exit_code == 0  # warning but success


class TestConfigGet:
    def test_get_existing(self) -> None:
        result = runner.invoke(app, ["config", "get", "default_host"])
        assert result.exit_code == 0
        assert "default_host" in result.output

    def test_get_unknown_exits(self) -> None:
        result = runner.invoke(app, ["config", "get", "nope"])
        assert result.exit_code == 1


class TestConfigList:
    def test_list(self) -> None:
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "default_host" in result.output


class TestConfigReset:
    def test_reset_requires_force(self) -> None:
        result = runner.invoke(app, ["config", "reset"])
        assert result.exit_code == 0

    def test_reset_with_force(self, _config_with_tmpfile) -> None:
        result = runner.invoke(app, ["config", "reset", "--force"])
        assert result.exit_code == 0


class TestConfigPath:
    def test_path(self) -> None:
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
