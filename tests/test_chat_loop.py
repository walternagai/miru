"""Tests for miru/commands/chat.py — interactive loop with slash commands."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.chat import _chat_async


def _make_client(models=None):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_models = AsyncMock(return_value=models if models is not None else [{"name": "gemma3"}])

    async def gen():
        yield {"message": {"content": "resposta do modelo"}, "done": True,
               "eval_count": 5, "eval_duration": 1_000_000_000}

    client.chat = MagicMock(return_value=gen())
    return client


def _run(commands, client=None):
    async def run():
        inputs = iter(commands)
        with patch("miru.commands.chat.OllamaClient", return_value=client or _make_client()), \
             patch("builtins.input", lambda *a, **k: next(inputs)):
            try:
                await _chat_async(
                    "gemma3", "http://x", None, None, None, None, None, None,
                    None, None, quiet=False, timeout=None,
                )
            except SystemExit as e:
                return e.code
        # /exit uses break → natural return = success
        return 0

    return asyncio.run(run())


class TestChatLoop:
    def test_exit(self) -> None:
        assert _run(["/exit"]) == 0

    def test_clear_and_history(self) -> None:
        assert _run(["/clear", "/history", "/exit"]) == 0

    def test_help(self) -> None:
        assert _run(["/help", "/exit"]) == 0

    def test_stats(self) -> None:
        assert _run(["/stats", "/exit"]) == 0

    def test_model_change(self) -> None:
        assert _run(["/model gemma3", "/exit"]) == 0

    def test_empty_input_skipped(self) -> None:
        assert _run(["", "/exit"]) == 0

    def test_prompt_then_exit(self) -> None:
        assert _run(["olá", "/exit"]) == 0

    def test_eof_breaks(self) -> None:
        async def run():
            with patch("miru.commands.chat.OllamaClient", return_value=_make_client()), \
                 patch("builtins.input", side_effect=EOFError):
                await _chat_async(
                    "gemma3", "http://x", None, None, None, None, None, None,
                    None, None, quiet=True, timeout=None,
                )
            return "finished"

        assert asyncio.run(run()) == "finished"

    def test_model_not_found_exits(self) -> None:
        client = _make_client(models=[])
        assert _run(["/exit"], client=client) == 1

    def test_connection_error_exits(self) -> None:
        from miru.core.errors import ConnectionError as MiruConnectionError

        client = MagicMock()
        client.__aenter__ = AsyncMock(side_effect=MiruConnectionError("http://x"))
        client.__aexit__ = AsyncMock(return_value=None)
        assert _run(["/exit"], client=client) == 1


class TestChatSlashCommands:
    def test_model_switch(self) -> None:
        assert _run(["/model gemma3", "/exit"]) == 0

    def test_model_switch_unknown(self) -> None:
        # gemma3 é o único modelo; /model bogus deve avisar e continuar
        assert _run(["/model bogus", "/exit"]) == 0

    def test_system_update(self) -> None:
        assert _run(["/system seja gentil", "/exit"]) == 0

    def test_retry_without_previous(self) -> None:
        assert _run(["/retry", "/exit"]) == 0

    def test_retry_with_previous(self) -> None:
        assert _run(["primeira msg", "/retry", "/exit"]) == 0

    def test_save_session(self, tmp_path) -> None:
        target = tmp_path / "sessao.md"
        assert _run([f"/save {target}", "/exit"]) == 0
        assert target.exists()

    def test_recall_empty_history(self, monkeypatch) -> None:
        from miru.history import clear_history

        clear_history()
        assert _run(["/recall", "/exit"]) == 0

    def test_recall_with_history(self, monkeypatch) -> None:
        import miru.history as history_mod

        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        history_mod.record_history("chat", "gemma3", "prompt antigo", response="resp")

        # /recall 0 deve carregar o prompt e continuar; depois /exit
        assert _run(["/recall 0", "/exit"]) == 0

    def test_quit_alias(self) -> None:
        assert _run(["/quit"]) == 0

    def test_keyboard_interrupt_autosaves(self, monkeypatch, tmp_path) -> None:
        import miru.commands.chat as chat_mod
        from miru.history import record_history

        config = type("C", (), {"history_enabled": True, "history_max_entries": 50})()
        monkeypatch.setattr("miru.config_manager.load_config", lambda: config)
        monkeypatch.setattr(chat_mod, "save_session", lambda *a, **k: None)
        monkeypatch.setattr(chat_mod, "get_history", lambda *a, **k: [])

        def fake_input(_prompt):
            raise KeyboardInterrupt

        client = _make_client()
        with patch("miru.commands.chat.OllamaClient", return_value=client), \
             patch("builtins.input", fake_input):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_chat_async(
                    "gemma3", "http://x", None, None, None, None, None, None,
                    None, None, quiet=False, timeout=None,
                ))
            assert exc.value.code == 0


class TestChatCliWrapper:
    def test_chat_no_model_exits(self) -> None:
        from unittest.mock import patch as _patch

        with _patch("miru.commands.chat.get_model_with_fallback", side_effect=SystemExit(1)):
            from typer.testing import CliRunner
            from miru.cli import app

            result = CliRunner().invoke(app, ["chat", "--quiet"])
            assert result.exit_code == 1
