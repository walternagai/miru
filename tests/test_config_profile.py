"""Tests for miru/commands/config_cmd.py profile management."""

from unittest.mock import patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _config_fixture(tmp_path, monkeypatch):
    import miru.commands.config_cmd as cfg_mod
    from miru.core.config import Config

    cfg = Config()
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setattr(cfg_mod, "load_config", lambda: cfg)
    monkeypatch.setattr(cfg_mod, "save_config", lambda c: None)
    return cfg


class TestConfigProfile:
    def test_list_empty(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "list"])
        assert result.exit_code == 0

    def test_create(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "create", "work"])
        assert result.exit_code == 0
        assert "work" in _config_fixture.profiles

    def test_create_duplicate_exits(self, _config_fixture) -> None:
        _config_fixture.profiles["work"] = {}
        result = runner.invoke(app, ["config", "profile", "create", "work"])
        assert result.exit_code == 1

    def test_create_without_name(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "create"])
        assert result.exit_code == 1

    def test_switch(self, _config_fixture) -> None:
        _config_fixture.profiles["work"] = {}
        result = runner.invoke(app, ["config", "profile", "switch", "work"])
        assert result.exit_code == 0
        assert _config_fixture.current_profile == "work"

    def test_switch_missing(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "switch", "nope"])
        assert result.exit_code == 1

    def test_delete(self, _config_fixture) -> None:
        _config_fixture.profiles["work"] = {}
        _config_fixture.current_profile = "work"
        result = runner.invoke(app, ["config", "profile", "delete", "work"])
        assert result.exit_code == 0
        assert "work" not in _config_fixture.profiles
        assert _config_fixture.current_profile is None

    def test_delete_missing(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "delete", "nope"])
        assert result.exit_code == 1

    def test_list_with_profiles(self, _config_fixture) -> None:
        _config_fixture.profiles["work"] = {"default_host": "http://x"}
        _config_fixture.current_profile = "work"
        result = runner.invoke(app, ["config", "profile", "list"])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_invalid_action(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "bogus"])
        assert result.exit_code == 1

    def test_set_action_hint(self, _config_fixture) -> None:
        result = runner.invoke(app, ["config", "profile", "set"])
        assert result.exit_code == 1
