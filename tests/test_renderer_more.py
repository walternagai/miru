"""Tests for miru/output/renderer.py — async render and compare tables."""

from unittest.mock import MagicMock, patch

import pytest

from miru.output import renderer as r
from miru.output.renderer import (
    create_progress_bar,
    render_compare_table,
    render_pull_progress,
    render_stream_as_markdown,
    stream_tokens,
)


async def _iter(chunks):
    for c in chunks:
        yield c


class TestStreamTokens:
    @pytest.mark.asyncio
    async def test_quiet_yields_all(self) -> None:
        chunks = [{"response": "a"}, {"response": "b", "done": True}]
        collected = [c async for c in stream_tokens(_iter(chunks), quiet=True)]
        assert len(collected) == 2

    @pytest.mark.asyncio
    async def test_non_quiet_prints(self, capsys) -> None:
        chunks = [{"response": "texto", "done": True, "eval_count": 1}]
        collected = [c async for c in stream_tokens(_iter(chunks), quiet=False)]
        assert len(collected) == 1
        assert "texto" in capsys.readouterr().out


class TestRenderStreamAsMarkdown:
    @pytest.mark.asyncio
    async def test_quiet_collects(self) -> None:
        chunks = [{"response": "resposta", "done": True}]
        text, final = await render_stream_as_markdown(_iter(chunks), quiet=True)
        assert text == "resposta"
        assert final is not None

    @pytest.mark.asyncio
    async def test_non_quiet_renders_markdown(self) -> None:
        chunks = [{"response": "# titulo", "done": True}]
        with patch.object(r, "console") as mock_console:
            text, final = await render_stream_as_markdown(_iter(chunks), quiet=False)
        assert text == "# titulo"
        assert mock_console.print.call_count >= 1

    @pytest.mark.asyncio
    async def test_empty_response(self) -> None:
        text, final = await render_stream_as_markdown(_iter([{"done": True}]), quiet=True)
        assert text == ""
        assert final is not None


class TestRenderModelsTableInternal:
    def test_empty_models(self) -> None:
        with patch.object(r, "console") as mock_console:
            r._render_models_table_internal([])
        assert mock_console.print.call_count >= 1

    def test_quiet_lists_names(self, capsys) -> None:
        r._render_models_table_internal([{"name": "a"}, {"name": "b"}], quiet=True)
        out = capsys.readouterr().out
        assert "a" in out and "b" in out

    def test_full_table(self) -> None:
        models = [{"name": "gemma3", "size": 1000, "modified_at": "2026-01-01T00:00:00"}]
        with patch.object(r, "console") as mock_console:
            r._render_models_table_internal(models)
        assert mock_console.print.call_count >= 1


class TestRenderPullProgress:
    @pytest.mark.asyncio
    async def test_quiet_success_prints(self, capsys) -> None:
        chunks = [{"status": "success"}]
        collected = [c async for c in render_pull_progress(_iter(chunks), "m", quiet=True)]
        assert len(collected) == 1
        assert "✓" in capsys.readouterr().out

    @pytest.mark.asyncio
    async def test_non_quiet_phases(self) -> None:
        chunks = [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 10, "total": 100},
            {"status": "success"},
        ]
        with patch.object(r, "console") as mock_console:
            collected = [c async for c in render_pull_progress(_iter(chunks), "m", quiet=False)]
        assert len(collected) == 3


class TestCompareTable:
    def test_empty_results(self) -> None:
        with patch.object(r, "console") as mock_console:
            render_compare_table([])
        assert mock_console.print.call_count >= 1

    def test_with_results(self) -> None:
        results = [
            MagicMock(model="a", prompt="p", response="r", eval_count=10,
                      eval_duration_ns=1_000_000_000, total_duration_ns=2_000_000_000,
                      tokens_per_second=10.0, error=None),
        ]
        with patch.object(r, "console") as mock_console:
            render_compare_table(results)
        assert mock_console.print.call_count >= 1


class TestCreateProgressBar:
    def test_creates_progress(self) -> None:
        progress = create_progress_bar()
        assert progress is not None
