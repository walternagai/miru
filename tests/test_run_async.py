"""Tests for miru/commands/run.py — _run_async success and error paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.run import _run_async


def _make_client(stream=False):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_models = AsyncMock(return_value=[{"name": "gemma3"}])

    async def gen():
        yield {"response": "resposta", "done": True, "eval_count": 3, "eval_duration": 1_000_000_000}

    client.generate = MagicMock(return_value=gen())
    client.chat = MagicMock(return_value=gen())
    return client


def _run(**kwargs):
    defaults = dict(
        model="gemma3", prompt="olá", host="http://x", system_prompt=None,
        images=[], files=[], audio=None, temperature=None, top_p=None,
        top_k=None, max_tokens=None, seed=None, repeat_penalty=None, ctx=None,
        no_stream=False, output_format="text", quiet=True, timeout=None,
        enable_tools=False, enable_tavily=False, sandbox_dir=None, tool_mode="auto_safe",
    )
    defaults.update(kwargs)
    return defaults


class TestRunAsync:
    def test_simple_generate(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run()))

    def test_no_stream_json(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(no_stream=True, output_format="json")))

    def test_quiet_text_stream(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(no_stream=False)))

    def test_system_prompt_chat(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(system_prompt="seja gentil")))

    def test_model_not_found(self) -> None:
        from miru.ollama.client import OllamaModelNotFound

        client = _make_client()
        client.generate = MagicMock(side_effect=OllamaModelNotFound("x"))
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run()))
        assert exc.value.code == 1

    def test_connection_error(self) -> None:
        from miru.ollama.client import OllamaConnectionError

        client = MagicMock()
        client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("down"))
        client.__aexit__ = AsyncMock(return_value=None)
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run()))
        assert exc.value.code == 1

    def test_vision_model_required(self) -> None:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.list_models = AsyncMock(return_value=[{"name": "gemma3"}])
        caps = MagicMock()
        caps.supports_vision = False
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.get_capabilities", new_callable=AsyncMock, return_value=caps):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(images=["foto.png"])))
        assert exc.value.code == 1

    def test_missing_file(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(files=["nope.txt"])))
        assert exc.value.code == 1
