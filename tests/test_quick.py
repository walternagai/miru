"""Tests for miru/commands/quick.py — quick commands."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from miru.cli import app
from miru.commands.quick import _extract_params
from typer.testing import CliRunner

runner = CliRunner()


class TestExtractParams:
    def test_extracts_placeholders(self) -> None:
        assert _extract_params("Write {language} code for {task}") == ["language", "task"]

    def test_no_params(self) -> None:
        assert _extract_params("Plain text") == []


class TestQuickList:
    def test_list(self) -> None:
        result = runner.invoke(app, ["quick", "--list", "code"])
        assert result.exit_code == 0
        assert "code" in result.output

    def test_list_via_command(self) -> None:
        result = runner.invoke(app, ["quick", "list"])
        assert result.exit_code == 0


class TestQuickRun:
    def _mock_client(self, chunks=None, models=None):
        chunks = chunks or [{"message": {"content": "resposta"}, "done": True, "eval_count": 10, "eval_duration": 1_000_000_000}]
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.list_models = AsyncMock(return_value=models or [{"name": "gemma3"}])
        # chat() returns an async iterator consumed with `async for` (not awaited)
        client.chat = MagicMock(return_value=_async_iter(chunks))
        return client

    def test_missing_param_exits(self) -> None:
        result = runner.invoke(app, ["quick", "code", "gemma3"])  # no language/task
        assert result.exit_code == 1

    def test_unknown_command_exits(self) -> None:
        result = runner.invoke(app, ["quick", "bogus", "gemma3", "--param", "x=1"])
        assert result.exit_code == 1

    def test_invalid_param_format(self) -> None:
        result = runner.invoke(app, ["quick", "code", "gemma3", "--param", "noequals"])
        assert result.exit_code == 1

    def test_no_model_and_no_default(self, monkeypatch) -> None:
        cfg = MagicMock()
        cfg.default_model = None
        monkeypatch.setattr("miru.commands.quick.load_config", lambda: cfg)
        result = runner.invoke(app, ["quick", "code"])
        assert result.exit_code == 1

    def test_successful_run(self) -> None:
        client = self._mock_client()
        with patch("miru.commands.quick.OllamaClient", return_value=client):
            result = runner.invoke(
                app, ["quick", "code", "gemma3", "--param", "language=python", "--param", "task=say hi"]
            )
        assert result.exit_code == 0
        assert "resposta" in result.output
    def test_connection_error(self) -> None:
        from miru.ollama.client import OllamaConnectionError

        client = AsyncMock()
        client.list_models = AsyncMock(side_effect=OllamaConnectionError("Cannot connect"))
        with patch("miru.commands.quick.OllamaClient", return_value=client):
            result = runner.invoke(app, ["quick", "code", "gemma3", "--param", "language=python", "--param", "task=x"])
        assert result.exit_code == 1


def _async_iter(items):
    async def gen():
        for i in items:
            yield i

    return gen()
