"""Tests for miru/commands/batch.py — prompt file parsing and processing."""

import json
from unittest.mock import MagicMock, patch

import pytest

from miru.commands.batch import (
    BatchResult,
    _calculate_tokens_per_second,
    _process_single_prompt,
    _read_prompts_file,
)


class TestCalculateTokensPerSecond:
    def test_zero_duration(self) -> None:
        assert _calculate_tokens_per_second(10, 0) == 0.0

    def test_normal(self) -> None:
        assert _calculate_tokens_per_second(100, 1_000_000_000) == 100.0


class TestReadPromptsFile:
    def test_plain_lines(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("primeiro\nsegundo\n", encoding="utf-8")
        assert _read_prompts_file(str(f)) == ["primeiro", "segundo"]

    def test_jsonl_lines(self, tmp_path) -> None:
        f = tmp_path / "p.jsonl"
        f.write_text(json.dumps({"prompt": "a"}) + "\n" + json.dumps({"text": "b"}) + "\n", encoding="utf-8")
        assert _read_prompts_file(str(f)) == ["a", "b"]

    def test_corrupt_json_falls_back_to_line(self, tmp_path) -> None:
        f = tmp_path / "p.txt"
        f.write_text("{not json\nplain\n", encoding="utf-8")
        assert _read_prompts_file(str(f)) == ["{not json", "plain"]

    def test_missing_file_exits(self) -> None:
        with pytest.raises(SystemExit):
            _read_prompts_file("nope.txt")

    def test_empty_file_exits(self, tmp_path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("  \n\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            _read_prompts_file(str(f))

    def test_directory_exits(self, tmp_path) -> None:
        with pytest.raises(SystemExit):
            _read_prompts_file(str(tmp_path))


class TestProcessSinglePrompt:
    @pytest.mark.asyncio
    async def test_with_system_prompt(self) -> None:
        client = MagicMock()
        chunks = [
            {"message": {"content": "resp"}, "done": True, "eval_count": 3,
             "eval_duration": 1_000_000_000, "total_duration": 1_000_000_000},
        ]
        client.chat = MagicMock(return_value=_async_iter(chunks))
        result = await _process_single_prompt(
            client, "m", "prompt", "sys", {}, stream=False, quiet=True
        )
        assert result.success is True
        assert result.response == "resp"
        assert result.eval_count == 3

    @pytest.mark.asyncio
    async def test_without_system_prompt(self) -> None:
        client = MagicMock()
        chunks = [{"response": "r", "done": True}]
        client.generate = MagicMock(return_value=_async_iter(chunks))
        result = await _process_single_prompt(
            client, "m", "prompt", None, {}, stream=False, quiet=True
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_no_final_chunk(self) -> None:
        client = MagicMock()
        client.chat = MagicMock(return_value=_async_iter([{"message": {"content": "x"}}]))
        result = await _process_single_prompt(
            client, "m", "prompt", "sys", {}, stream=False, quiet=True
        )
        assert result.success is False
        assert "No final chunk" in (result.error or "")

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        client = MagicMock()
        client.chat = MagicMock(side_effect=RuntimeError("boom"))
        result = await _process_single_prompt(
            client, "m", "prompt", "sys", {}, stream=False, quiet=True
        )
        assert result.success is False
        assert result.error is not None


class TestBatchResult:
    def test_defaults(self) -> None:
        r = BatchResult("p", "r", True)
        assert r.error is None


def _async_iter(items):
    async def gen():
        for i in items:
            yield i

    return gen()
