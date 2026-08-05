"""Tests for miru/session.py — session persistence, favorites and export."""

import json

import pytest

import miru.session as session_mod
from miru.session import (
    delete_session,
    export_session,
    get_session_path,
    is_favorite,
    list_sessions,
    load_favorites,
    load_session,
    save_favorites,
    save_session,
    toggle_favorite,
)


@pytest.fixture(autouse=True)
def _isolate_session_dir(tmp_path, monkeypatch):
    """Point session paths at a tmp dir so tests never touch ~/.miru."""
    sessions_dir = tmp_path / "sessions"
    favorites_file = tmp_path / "favorites.json"
    monkeypatch.setattr(session_mod, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(session_mod, "FAVORITES_FILE", favorites_file)
    # Reset the module-level favorites cache between tests
    session_mod._favorites_cache._data = None
    session_mod._favorites_cache._mtime = 0.0


class TestFavorites:
    def test_load_favorites_empty_when_no_file(self) -> None:
        assert load_favorites() == set()

    def test_save_and_load_roundtrip(self) -> None:
        save_favorites({"a", "b"})
        assert load_favorites() == {"a", "b"}

    def test_toggle_adds_and_removes(self) -> None:
        assert toggle_favorite("s1") is True
        assert is_favorite("s1") is True
        assert toggle_favorite("s1") is False
        assert is_favorite("s1") is False

    def test_favorites_survive_cache_clear(self) -> None:
        save_favorites({"keep"})
        session_mod._favorites_cache._data = None
        assert load_favorites() == {"keep"}


class TestSessionPersistence:
    def test_save_and_load_roundtrip(self) -> None:
        save_session("conv1", "gemma3", [{"role": "user", "content": "oi"}], system_prompt="sp")
        data = load_session("conv1")
        assert data is not None
        assert data["name"] == "conv1"
        assert data["model"] == "gemma3"
        assert data["system_prompt"] == "sp"
        assert data["messages"] == [{"role": "user", "content": "oi"}]
        assert data["version"] == 1
        assert "created" in data and "updated" in data

    def test_save_preserves_original_created(self) -> None:
        save_session("conv1", "m", [])
        original = load_session("conv1")["created"]
        save_session("conv1", "m2", [{"role": "user", "content": "x"}])
        assert load_session("conv1")["created"] == original
        assert load_session("conv1")["model"] == "m2"

    def test_load_missing_returns_none(self) -> None:
        assert load_session("nope") is None

    def test_delete_returns_bool(self) -> None:
        save_session("conv1", "m", [])
        assert delete_session("conv1") is True
        assert delete_session("conv1") is False
        assert load_session("conv1") is None

    def test_get_session_path(self) -> None:
        assert get_session_path("a b").name == "a b.json"

    def test_list_sessions_sorted_by_updated(self) -> None:
        save_session("old", "m", [])
        save_session("new", "m", [])
        names = [s["name"] for s in list_sessions()]
        assert set(names) == {"old", "new"}
        assert names[0] == "new"  # most recent first

    def test_list_sessions_metadata(self) -> None:
        save_session("meta", "llama3", [{"role": "user", "content": "1"}, {"role": "assistant", "content": "2"}])
        sessions = list_sessions()
        assert sessions[0]["turns"] == 1
        assert sessions[0]["model"] == "llama3"

    def test_load_corrupt_session_returns_none(self, tmp_path) -> None:
        session_mod.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (session_mod.SESSIONS_DIR / "bad.json").write_text("{not json", encoding="utf-8")
        assert load_session("bad") is None


class TestExport:
    def _save_sample(self) -> str:
        save_session(
            "exp",
            "m",
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "pergunta"},
                {"role": "assistant", "content": "resposta"},
            ],
        )
        return "exp"

    def test_export_json(self, tmp_path) -> None:
        name = self._save_sample()
        out = tmp_path / "out.json"
        export_session(name, str(out), "json")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["name"] == name
        assert len(data["messages"]) == 3

    def test_export_markdown(self, tmp_path) -> None:
        name = self._save_sample()
        out = tmp_path / "out.md"
        export_session(name, str(out), "markdown")
        text = out.read_text(encoding="utf-8")
        assert "Chat Session" in text
        assert "pergunta" in text
        assert "resposta" in text
        assert "sys" not in text  # system messages skipped

    def test_export_txt(self, tmp_path) -> None:
        name = self._save_sample()
        out = tmp_path / "out.txt"
        export_session(name, str(out), "txt")
        text = out.read_text(encoding="utf-8")
        assert "[USER]" in text
        assert "[ASSISTANT]" in text

    def test_export_default_output_name(self, tmp_path, monkeypatch) -> None:
        name = self._save_sample()
        monkeypatch.chdir(tmp_path)
        export_session(name, format="json")
        assert (tmp_path / "exp.json").exists()

    def test_export_unsupported_format_exits(self, tmp_path) -> None:
        name = self._save_sample()
        with pytest.raises(SystemExit) as exc:
            export_session(name, str(tmp_path / "out.xyz"), "xyz")
        assert exc.value.code == 1

    def test_export_missing_session_exits(self, tmp_path) -> None:
        with pytest.raises(SystemExit) as exc:
            export_session("missing", str(tmp_path / "o.json"), "json")
        assert exc.value.code == 1
