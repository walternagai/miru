"""Tests for miru/history.py — prompt history persistence and search."""

import json

import pytest

import miru.history as history_mod
from miru.history import (
    HistoryEntry,
    clear_history,
    get_history,
    get_history_by_index,
    record_history,
    search_history,
)


@pytest.fixture(autouse=True)
def _isolate_history_file(tmp_path, monkeypatch):
    history_file = tmp_path / "history.jsonl"
    monkeypatch.setattr(history_mod, "HISTORY_FILE", history_file)


class TestHistoryEntry:
    def test_to_dict_from_dict_roundtrip(self) -> None:
        entry = HistoryEntry(
            timestamp="2026-01-01T00:00:00",
            command="run",
            model="gemma3",
            prompt="hello",
            system_prompt="sp",
            response="hi",
            success=True,
            metrics={"eval_count": 10},
        )
        assert HistoryEntry.from_dict(entry.to_dict()) == entry

    def test_defaults(self) -> None:
        entry = HistoryEntry(timestamp="t", command="c", model="m", prompt="p")
        assert entry.success is True
        assert entry.error is None
        assert entry.response is None


class TestRecordAndGet:
    def test_record_when_disabled(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": False, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "m", "p")
        assert get_history() == []

    def test_record_and_read_back(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "gemma3", "olá mundo", response="resposta")
        entries = get_history()
        assert len(entries) == 1
        assert entries[0].command == "run"
        assert entries[0].model == "gemma3"
        assert entries[0].prompt == "olá mundo"
        assert entries[0].response == "resposta"

    def test_long_response_truncated(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "m", "p", response="x" * 1500)
        entries = get_history()
        assert len(entries[0].response or "") <= 1004

    def test_long_prompt_truncated(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "m", "p" * 700)
        assert len(get_history()[0].prompt) == 500

    def test_rotation_respects_max(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 3})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        for i in range(5):
            record_history("run", "m", f"prompt-{i}")
        entries = get_history()
        assert len(entries) == 3
        prompts = {e.prompt for e in entries}
        assert "prompt-2" in prompts and "prompt-4" in prompts
        assert "prompt-0" not in prompts

    def test_get_history_filter_by_command(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "m", "a")
        record_history("chat", "m", "b")
        commands = {e.command for e in get_history(command="run")}
        assert commands == {"run"}

    def test_get_history_limit(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        for i in range(5):
            record_history("run", "m", f"p{i}")
        assert len(get_history(limit=2)) == 2

    def test_get_history_missing_file(self) -> None:
        assert get_history() == []


class TestSearchAndClear:
    def _seed(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        record_history("run", "m", "python lambda", response="code snippet")
        record_history("chat", "m", "receita bolo", response="ingredientes")

    def test_search_matches_prompt(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        results = search_history("python")
        assert len(results) == 1
        assert results[0].prompt == "python lambda"

    def test_search_matches_response(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        results = search_history("ingredientes")
        assert len(results) == 1
        assert results[0].command == "chat"

    def test_search_case_insensitive(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        assert len(search_history("PYTHON")) == 1

    def test_search_no_match(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        assert search_history("zzz") == []

    def test_get_by_index(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        entry = get_history_by_index(0)
        assert entry is not None
        assert entry.prompt in ("python lambda", "receita bolo")
        assert get_history_by_index(99) is None

    def test_clear_history(self, monkeypatch) -> None:
        self._seed(monkeypatch)
        assert len(get_history()) == 2
        clear_history()
        assert get_history() == []

    def test_corrupt_history_returns_empty(self, tmp_path) -> None:
        history_mod.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history_mod.HISTORY_FILE.write_text("{bad json\n", encoding="utf-8")
        assert get_history() == []
        assert search_history("x") == []

    def _write_lines(self, *lines: str) -> None:
        history_mod.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history_mod.HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _entry_line(self, prompt: str, command: str = "run") -> str:
        return json.dumps(
            HistoryEntry(timestamp="2026-01-01T00:00:00", command=command, model="m", prompt=prompt).to_dict(),
            ensure_ascii=False,
        )

    def test_corrupt_line_between_valid_entries_is_skipped(self) -> None:
        self._write_lines(
            self._entry_line("first"),
            "{bad json",
            self._entry_line("second"),
        )
        entries = get_history()
        assert [e.prompt for e in entries] == ["second", "first"]
        assert {e.prompt for e in search_history("s")} == {"first", "second"}

    def test_append_after_corrupt_line_preserves_valid_entries(self, monkeypatch) -> None:
        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)

        self._write_lines(
            self._entry_line("first"),
            "{bad json",
            self._entry_line("second"),
        )
        record_history("run", "m", "third")

        entries = get_history()
        assert {e.prompt for e in entries} == {"first", "second", "third"}
        assert len(entries) == 3

    def test_append_after_corrupt_line_rewrites_valid_lines_only(self) -> None:
        self._write_lines(self._entry_line("only"), "not json at all")
        history_mod._append_history(
            HistoryEntry(timestamp="2026-01-01T00:00:00", command="run", model="m", prompt="new"),
            max_entries=50,
        )

        lines = [ln for ln in history_mod.HISTORY_FILE.read_text(encoding="utf-8").splitlines() if ln]
        assert len(lines) == 2
        assert all(json.loads(ln) for ln in lines)
