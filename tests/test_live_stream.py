"""Tests for miru/output/live_stream.py."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from miru.output.live_stream import (
    stream_as_markdown_live,
    _detect_code_blocks,
    _has_incomplete_code_block,
    _get_incomplete_code_block,
    _render_with_syntax_highlight,
)


class TestDetectCodeBlocks:
    """Tests for _detect_code_blocks function."""

    def test_no_code_blocks(self) -> None:
        """Should return empty list for no code blocks."""
        text = "Just regular text without code blocks."
        _, code_blocks = _detect_code_blocks(text)
        assert code_blocks == []

    def test_complete_code_block(self) -> None:
        """Should detect complete code block."""
        text = "```python\nprint('hello')\n```"
        _, code_blocks = _detect_code_blocks(text)
        assert len(code_blocks) == 1
        assert code_blocks[0][0] == "python"
        assert "print('hello')" in code_blocks[0][1]

    def test_code_block_without_language(self) -> None:
        """Should default to 'text' for code block without language."""
        text = "```\nsome code\n```"
        _, code_blocks = _detect_code_blocks(text)
        assert len(code_blocks) == 1
        assert code_blocks[0][0] == "text"

    def test_multiple_code_blocks(self) -> None:
        """Should detect multiple code blocks."""
        text = "```python\nprint('hello')\n```\n\n```javascript\nconsole.log('hi');\n```"
        _, code_blocks = _detect_code_blocks(text)
        assert len(code_blocks) == 2
        assert code_blocks[0][0] == "python"
        assert code_blocks[1][0] == "javascript"


class TestHasIncompleteCodeBlock:
    """Tests for _has_incomplete_code_block function."""

    def test_no_code_blocks(self) -> None:
        """Should return False for no code blocks."""
        text = "Just text"
        assert _has_incomplete_code_block(text) is False

    def test_complete_code_block(self) -> None:
        """Should return False for complete code block."""
        text = "```python\nprint('hello')\n```"
        assert _has_incomplete_code_block(text) is False

    def test_incomplete_code_block(self) -> None:
        """Should return True for incomplete code block."""
        text = "```python\nprint('hello')"
        assert _has_incomplete_code_block(text) is True

    def test_odd_number_of_fences(self) -> None:
        """Should return True for odd number of fences."""
        text = "```python\ncode```\n\n```javascript\nmore"
        assert _has_incomplete_code_block(text) is True


class TestGetIncompleteCodeBlock:
    """Tests for _get_incomplete_code_block function."""

    def test_no_incomplete_block(self) -> None:
        """Should return None when no incomplete block."""
        text = "```python\ncode\n```"
        assert _get_incomplete_code_block(text) is None

    def test_incomplete_block_with_language(self) -> None:
        """Should return language for incomplete block."""
        text = "```python\nprint('hello')"
        result = _get_incomplete_code_block(text)
        assert result is not None
        assert "print('hello')" in result

    def test_incomplete_block_without_language(self) -> None:
        """Should handle block without language."""
        text = "```\nsome code"
        result = _get_incomplete_code_block(text)
        assert result is not None
        assert "some code" in result

    def test_empty_incomplete_block(self) -> None:
        """Should handle empty incomplete block."""
        text = "```python\n"
        result = _get_incomplete_code_block(text)
        # Empty content after language, but before newline
        assert result == ""


class TestRenderWithSyntaxHighlight:
    """Tests for _render_with_syntax_highlight function."""

    def test_plain_text(self) -> None:
        """Should render plain text as Markdown."""
        text = "This is plain text"
        md = _render_with_syntax_highlight(text)
        assert md is not None

    def test_text_with_complete_code_block(self) -> None:
        """Should render code block in Markdown."""
        text = "```python\nprint('hello')\n```"
        md = _render_with_syntax_highlight(text)
        assert md is not None

    def test_text_with_incomplete_code_block(self) -> None:
        """Should render incomplete code block as text."""
        text = "```python\nprint('hello')"
        md = _render_with_syntax_highlight(text)
        assert md is not None


class TestStreamAsMarkdownLive:
    """Tests for stream_as_markdown_live function."""

    @pytest.mark.asyncio
    async def test_quiet_mode_returns_text(self) -> None:
        """Should return text without rendering."""
        chunks = [
            {"response": "Hello"},
            {"response": " "},
            {"response": "World", "done": True, "eval_count": 10, "total_duration": 1_000_000_000},
        ]

        text, final_chunk = await stream_as_markdown_live(
            self._async_iter(chunks), quiet=True, show_metrics=False
        )

        assert text == "Hello World"
        assert final_chunk is not None
        assert final_chunk.get("done") is True

    @pytest.mark.asyncio
    async def test_quiet_mode_with_chat_format(self) -> None:
        """Should handle chat format (message.content)."""
        chunks = [
            {"message": {"content": "Hello"}},
            {"message": {"content": " "}},
            {"message": {"content": "World"}, "done": True, "eval_count": 15},
        ]

        text, final_chunk = await stream_as_markdown_live(
            self._async_iter(chunks), quiet=True, show_metrics=False
        )

        assert text == "Hello World"
        assert final_chunk is not None

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_empty(self) -> None:
        """Should handle empty chunks."""
        chunks = [
            {"response": ""},
            {"done": True, "eval_count": 0},
        ]

        text, final_chunk = await stream_as_markdown_live(
            self._async_iter(chunks), quiet=True, show_metrics=False
        )

        assert text == ""
        assert final_chunk is not None

    @pytest.mark.asyncio
    @patch("miru.output.live_stream.Live")
    @patch("miru.output.live_stream.Markdown")
    async def test_live_rendering_updates(
        self, mock_markdown: MagicMock, mock_live: MagicMock
    ) -> None:
        """Should update Live display for each chunk."""
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=False)

        chunks = [
            {"response": "Line 1\n"},
            {"response": "Line 2\n", "done": True, "eval_count": 20, "total_duration": 500_000_000},
        ]

        await stream_as_markdown_live(
            self._async_iter(chunks), quiet=False, show_metrics=False
        )

        assert mock_live_instance.update.call_count == 2
        mock_markdown.assert_called()

    @pytest.mark.asyncio
    @patch("miru.output.renderer.render_metrics")
    @patch("miru.output.live_stream.Live")
    @patch("miru.output.live_stream.Markdown")
    async def test_show_metrics_calls_render_metrics(
        self, mock_markdown: MagicMock, mock_live: MagicMock, mock_render_metrics: MagicMock
    ) -> None:
        """Should call render_metrics when show_metrics=True."""
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=False)

        chunks = [
            {"response": "Test", "done": True, "eval_count": 5, "total_duration": 100_000_000},
        ]

        await stream_as_markdown_live(
            self._async_iter(chunks), quiet=False, show_metrics=True
        )

        mock_render_metrics.assert_called_once()

    @pytest.mark.asyncio
    @patch("miru.output.renderer.render_metrics")
    @patch("miru.output.live_stream.Live")
    @patch("miru.output.live_stream.Markdown")
    async def test_no_metrics_on_empty_response(
        self, mock_markdown: MagicMock, mock_live: MagicMock, mock_render_metrics: MagicMock
    ) -> None:
        """Should not call render_metrics on empty response."""
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=False)

        chunks = [
            {"response": "", "done": True},
        ]

        await stream_as_markdown_live(
            self._async_iter(chunks), quiet=False, show_metrics=True
        )

        mock_render_metrics.assert_not_called()

    @pytest.mark.asyncio
    @patch("miru.output.renderer.render_metrics")
    @patch("miru.output.live_stream.Live")
    @patch("miru.output.live_stream.Markdown")
    async def test_code_block_streaming(
        self, mock_markdown: MagicMock, mock_live: MagicMock, mock_render_metrics: MagicMock
    ) -> None:
        """Should handle code blocks during streaming."""
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=False)

        chunks = [
            {"response": "```python\n"},
            {"response": "print('hello')\n"},
            {"response": "```\n", "done": True, "eval_count": 10},
        ]

        await stream_as_markdown_live(
            self._async_iter(chunks), quiet=False, show_metrics=False
        )

        # Should update for each chunk
        assert mock_live_instance.update.call_count == 3

    @staticmethod
    def _async_iter(items: list):
        """Helper to create async iterator from list."""
        async def async_generator():
            for item in items:
                yield item
        return async_generator()