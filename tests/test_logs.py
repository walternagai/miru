"""Tests for miru/commands/logs.py — log file listing and viewing."""

import json

import pytest

import miru.commands.logs as logs_mod
from miru.cli import app
from miru.commands.logs import clear_logs, get_log_files
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def log_dir(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(logs_mod, "LOG_DIR", log_dir)
    return log_dir


def _write_log(log_dir, name="miru_20260101_000000.log", lines=None):
    lines = lines or [
        json.dumps({"timestamp": "2026-01-01T00:00:00", "level": "INFO", "message": "started"}),
        "raw line without json",
    ]
    f = log_dir / name
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f


class TestGetLogFiles:
    def test_empty_when_no_dir(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logs_mod, "LOG_DIR", tmp_path / "nope")
        assert get_log_files() == []

    def test_lists_only_miru_logs(self, tmp_path, monkeypatch) -> None:
        log_dir = tmp_path / "logs2"
        log_dir.mkdir()
        (log_dir / "miru_1.log").write_text("x")
        (log_dir / "other.txt").write_text("x")
        monkeypatch.setattr(logs_mod, "LOG_DIR", log_dir)
        files = get_log_files()
        assert len(files) == 1
        assert files[0].name == "miru_1.log"


class TestLogsCommand:
    def test_empty(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logs_mod, "LOG_DIR", tmp_path / "empty")
        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0

    def test_list_files(self, log_dir) -> None:
        _write_log(log_dir)
        result = runner.invoke(app, ["logs", "--list"])
        assert result.exit_code == 0
        assert "miru_20260101_000000.log" in result.output

    def test_list_empty(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logs_mod, "LOG_DIR", tmp_path / "empty")
        result = runner.invoke(app, ["logs", "--list"])
        assert result.exit_code == 0

    def test_show_lines(self, log_dir) -> None:
        _write_log(log_dir)
        result = runner.invoke(app, ["logs"])
        assert result.exit_code == 0
        assert "started" in result.output

    def test_latest_flag(self, log_dir) -> None:
        _write_log(log_dir, "miru_old.log")
        _write_log(log_dir, "miru_new.log")
        result = runner.invoke(app, ["logs", "--latest"])
        assert result.exit_code == 0
        assert "miru_new.log" in result.output


class TestClearLogs:
    def test_requires_force(self, log_dir) -> None:
        _write_log(log_dir)
        clear_logs()
        assert len(list(log_dir.iterdir())) == 1

    def test_force_clears(self, log_dir) -> None:
        _write_log(log_dir)
        _write_log(log_dir, "miru_2.log")
        clear_logs(force=True)
        assert list(log_dir.iterdir()) == []

    def test_clear_empty(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(logs_mod, "LOG_DIR", tmp_path / "empty")
        clear_logs(force=True)  # no raise
