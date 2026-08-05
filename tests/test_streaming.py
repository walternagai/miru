"""Tests for miru/output/streaming.py — render_stream, JSON output, collect."""

import json

import pytest

from miru.output.streaming import collect_stream, render_json_output, render_stream


async def _iter(chunks):
    for c in chunks:
        yield c


class TestCollectStream:
    @pytest.mark.asyncio
    async def test_collects_response_and_message_chunks(self) -> None:
        chunks = [
            {"response": "Hello "},
            {"message": {"content": "World"}},
            {"done": True, "model": "gemma3"},
        ]
        text, final, model = await collect_stream(_iter(chunks))
        assert text == "Hello World"
        assert final is not None
        assert model == "gemma3"

    @pytest.mark.asyncio
    async def test_empty_stream(self) -> None:
        text, final, model = await collect_stream(_iter([]))
        assert text == ""
        assert final is None
        assert model is None


class TestRenderJsonOutput:
    def test_output_structure(self, capsys) -> None:
        render_json_output(
            model="m", prompt="p", response="r",
            metrics={"eval_count": 5, "eval_duration": 1_000_000_000,
                     "total_duration": 1_500_000_000},
        )
        out = json.loads(capsys.readouterr().out)
        assert out["model"] == "m"
        assert out["prompt"] == "p"
        assert out["response"] == "r"
        assert out["metrics"]["tokens_per_second"] == 5.0

    def test_output_without_metrics(self, capsys) -> None:
        render_json_output(model="m", prompt="p", response="r", metrics=None)
        out = json.loads(capsys.readouterr().out)
        assert "metrics" not in out


class TestRenderStream:
    @pytest.mark.asyncio
    async def test_quiet_mode_no_output(self, capsys) -> None:
        final = await render_stream(
            _iter([{"response": "x", "done": True}]), quiet=True
        )
        assert capsys.readouterr().out == ""
        assert final is not None

    @pytest.mark.asyncio
    async def test_text_mode_prints_tokens(self, capsys) -> None:
        await render_stream(
            _iter([{"response": "linha1\n"}, {"response": "linha2"}]), quiet=False
        )
        out = capsys.readouterr().out
        assert "linha1" in out and "linha2" in out

    @pytest.mark.asyncio
    async def test_json_mode_prints_final_json(self, capsys) -> None:
        final = await render_stream(
            _iter([{"response": "resp", "done": True, "model": "m"}]),
            quiet=False, output_format="json",
        )
        out = json.loads(capsys.readouterr().out)
        assert out["response"] == "resp"
        assert out["model"] == "m"
        assert final is not None

    @pytest.mark.asyncio
    async def test_text_mode_no_trailing_newline_issue(self, capsys) -> None:
        # A single text chunk must print its content
        await render_stream(_iter([{"response": "only"}]), quiet=False)
        assert "only" in capsys.readouterr().out
