"""Tests for miru/commands/history_cmd.py — history CLI commands."""

import json

import pytest

import miru.history as history_mod
from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_history(tmp_path, monkeypatch):
    history_file = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", history_file)
    config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
    monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
    yield


def _seed_entries(monkeypatch):
    for cmd, prompt in [("run", "primeiro prompt"), ("chat", "segundo prompt")]:
        history_mod.record_history(cmd, "gemma3", prompt, response="resp")


class TestHistoryCmd:
    def test_clear(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "--clear"])
        assert result.exit_code == 0
        assert history_mod.get_history() == []

    def test_empty_history(self) -> None:
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0

    def test_json_format(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["command"] == "chat"  # most recent first

    def test_text_format_shows_entries(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "primeiro prompt" in result.output or "segundo prompt" in result.output

    def test_filter_by_command(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "--command", "run"])
        assert result.exit_code == 0
        assert "primeiro prompt" in result.output

    def test_search(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "--search", "segundo"])
        assert result.exit_code == 0
        assert "segundo prompt" in result.output

    def test_pagination_via_limit(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "--limit", "1"])
        assert result.exit_code == 0

    def test_list_subcommand(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "list", "--limit", "1"])
        assert result.exit_code == 0


class TestHistoryShow:
    def test_show_existing(self) -> None:
        _seed_entries(None)
        result = runner.invoke(app, ["history", "show", "0"])
        assert result.exit_code == 0
        assert "segundo prompt" in result.output

    def test_show_missing_exits(self) -> None:
        result = runner.invoke(app, ["history", "show", "99"])
        assert result.exit_code == 1
