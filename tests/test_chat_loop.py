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
