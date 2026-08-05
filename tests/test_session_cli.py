"""Tests for miru/session.py CLI — list/show/delete/export/rename commands."""

import json

import pytest

import miru.session as session_mod
from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    favorites_file = tmp_path / "favorites.json"
    monkeypatch.setattr(session_mod, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(session_mod, "FAVORITES_FILE", favorites_file)
    session_mod._favorites_cache._data = None
    session_mod._favorites_cache._mtime = 0.0


class TestSessionCli:
    def test_list_empty(self) -> None:
        result = runner.invoke(app, ["session", "list"])
        assert result.exit_code == 0

    def test_list_with_session(self) -> None:
        session_mod.save_session("conv1", "gemma3", [{"role": "user", "content": "oi"}])
        result = runner.invoke(app, ["session", "list"])
        assert result.exit_code == 0
        assert "conv1" in result.output

    def test_show_existing(self) -> None:
        session_mod.save_session("conv1", "gemma3", [{"role": "user", "content": "oi"}])
        result = runner.invoke(app, ["session", "show", "conv1"])
        assert result.exit_code == 0
        assert "conv1" in result.output

    def test_show_missing_exits(self) -> None:
        result = runner.invoke(app, ["session", "show", "nope"])
        assert result.exit_code == 1

    def test_delete_requires_force(self) -> None:
        session_mod.save_session("conv1", "m", [])
        result = runner.invoke(app, ["session", "delete", "conv1"])
        assert result.exit_code == 0
        assert session_mod.load_session("conv1") is not None

    def test_delete_with_force(self) -> None:
        session_mod.save_session("conv1", "m", [])
        result = runner.invoke(app, ["session", "delete", "conv1", "--force"])
        assert result.exit_code == 0
        assert session_mod.load_session("conv1") is None

    def test_delete_missing_exits(self) -> None:
        result = runner.invoke(app, ["session", "delete", "nope", "--force"])
        assert result.exit_code == 1

    def test_export(self, tmp_path, monkeypatch) -> None:
        session_mod.save_session("conv1", "m", [{"role": "user", "content": "oi"}])
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["session", "export", "conv1"])
        assert result.exit_code == 0
        assert (tmp_path / "conv1.json").exists()

    def test_export_missing_exits(self, tmp_path) -> None:
        result = runner.invoke(app, ["session", "export", "nope", "--output", str(tmp_path / "o.json")])
        assert result.exit_code == 1

    def test_rename(self) -> None:
        session_mod.save_session("old", "m", [{"role": "user", "content": "x"}])
        result = runner.invoke(app, ["session", "rename", "old", "new"])
        assert result.exit_code == 0
        assert session_mod.load_session("new") is not None
        assert session_mod.load_session("old") is None

    def test_rename_missing_exits(self) -> None:
        result = runner.invoke(app, ["session", "rename", "nope", "new"])
        assert result.exit_code == 1

    def test_rename_conflict_exits(self) -> None:
        session_mod.save_session("a", "m", [])
        session_mod.save_session("b", "m", [])
        result = runner.invoke(app, ["session", "rename", "a", "b"])
        assert result.exit_code == 1
