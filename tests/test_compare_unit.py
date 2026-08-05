"""Tests for miru/commands/compare.py — model comparison helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.compare import (
    ModelResult,
    _calculate_tokens_per_second,
    _execute_model,
)


class TestCalculateTokensPerSecond:
    def test_uses_eval_duration(self) -> None:
        assert _calculate_tokens_per_second(100, 1_000_000_000) == 100.0

    def test_falls_back_to_total_duration(self) -> None:
        assert _calculate_tokens_per_second(50, 0, 2_000_000_000) == 25.0

    def test_zero_when_no_duration(self) -> None:
        assert _calculate_tokens_per_second(10, 0, 0) == 0.0

    def test_zero_when_zero_seconds(self) -> None:
        assert _calculate_tokens_per_second(10, 0, 0) == 0.0


class TestExecuteModel:
    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self) -> None:
        client = MagicMock()
        chunks = [
            {"message": {"content": "olá"}, "done": True, "eval_count": 2,
             "eval_duration": 1_000_000_000, "total_duration": 2_000_000_000},
        ]
        client.chat = MagicMock(return_value=_async_iter(chunks))
        result = await _execute_model(
            client, "m", "prompt", "sys", None, {}, stream=False, quiet=True
        )
        assert result.response == "olá"
        assert result.error is None
        assert result.eval_count == 2

    @pytest.mark.asyncio
    async def test_generate_without_system(self) -> None:
        client = MagicMock()
        chunks = [
            {"response": "resposta", "done": True, "eval_count": 5,
             "eval_duration": 1_000_000_000, "total_duration": 1_000_000_000},
        ]
        client.generate = MagicMock(return_value=_async_iter(chunks))
        result = await _execute_model(
            client, "m", "prompt", None, None, {}, stream=False, quiet=True
        )
        assert result.response == "resposta"

    @pytest.mark.asyncio
    async def test_no_final_chunk(self) -> None:
        client = MagicMock()
        client.chat = MagicMock(return_value=_async_iter([{"message": {"content": "x"}}]))
        result = await _execute_model(
            client, "m", "prompt", "sys", None, {}, stream=False, quiet=True
        )
        assert result.error == "No final chunk received"

    @pytest.mark.asyncio
    async def test_exception_returns_error_result(self) -> None:
        client = MagicMock()
        client.chat = MagicMock(side_effect=RuntimeError("boom"))
        result = await _execute_model(
            client, "m", "prompt", "sys", None, {}, stream=False, quiet=True
        )
        assert result.error is not None


class TestModelResult:
    def test_defaults(self) -> None:
        r = ModelResult("m", "p", "r", 1, 2, 3, 4.0)
        assert r.error is None


def _async_iter(items):
    async def gen():
        for i in items:
            yield i

    return gen()
