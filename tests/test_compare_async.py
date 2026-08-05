"""Tests for miru/commands/compare.py — _compare_async integration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.compare import _compare_async
from miru.core.i18n import set_language


def _make_client():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_models = AsyncMock(return_value=[{"name": "a"}, {"name": "b"}])

    async def gen():
        yield {"message": {"content": "resp"}, "done": True, "eval_count": 3,
               "eval_duration": 1_000_000_000, "total_duration": 1_000_000_000}

    client.chat = MagicMock(return_value=gen())
    return client


class TestCompareAsync:
    @staticmethod
    def _ok_result(model="a"):
        r = MagicMock()
        r.error = None
        r.eval_count = 3
        r.total_duration_ns = 1_000_000_000
        r.tokens_per_second = 3.0
        r.model = model
        r.response = "r"
        return r

    @pytest.mark.asyncio
    async def test_success_both_models(self) -> None:
        client = _make_client()
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._execute_model", new_callable=AsyncMock,
                   side_effect=[self._ok_result("a"), self._ok_result("b")]), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            await _compare_async(
                ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                None, None, None, None, True, "text", quiet=True,
            )

    @pytest.mark.asyncio
    async def test_json_output(self) -> None:
        client = _make_client()
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._execute_model", new_callable=AsyncMock,
                   side_effect=[self._ok_result("a"), self._ok_result("b")]), \
             patch("miru.commands.compare._render_json_output") as mock_json:
            await _compare_async(
                ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                None, None, None, None, True, "json", quiet=True,
            )
        mock_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_failed_exits(self) -> None:
        client = _make_client()
        client.chat = MagicMock(side_effect=RuntimeError("boom"))
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            with pytest.raises(SystemExit) as exc:
                await _compare_async(
                    ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                    None, None, None, None, True, "text", quiet=True,
                )
        assert exc.value.code == 1

    @pytest.mark.asyncio
    async def test_vision_error_skips_model(self) -> None:
        client = _make_client()
        caps = MagicMock()
        caps.supports_vision = False
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare.encode_images", return_value=["b64"]), \
             patch("miru.commands.compare.get_capabilities", new_callable=AsyncMock, return_value=caps), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            with pytest.raises(SystemExit) as exc:
                await _compare_async(
                    ["a"], "prompt", None, "http://x", ["img.png"], None, None, None,
                    None, None, None, None, True, "text", quiet=True,
                )
        assert exc.value.code == 1

    @pytest.mark.asyncio
    async def test_all_failed_exits(self) -> None:
        client = _make_client()
        client.chat = MagicMock(side_effect=RuntimeError("boom"))
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            with pytest.raises(SystemExit) as exc:
                await _compare_async(
                    ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                    None, None, None, None, True, "text", quiet=True,
                )
        assert exc.value.code == 1

    @pytest.mark.asyncio
    async def test_vision_error_skips_model(self) -> None:
        client = _make_client()
        caps = MagicMock()
        caps.supports_vision = False
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare.encode_images", return_value=["b64"]), \
             patch("miru.commands.compare.get_capabilities", new_callable=AsyncMock, return_value=caps), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            with pytest.raises(SystemExit) as exc:
                await _compare_async(
                    ["a"], "prompt", None, "http://x", ["img.png"], None, None, None,
                    None, None, None, None, True, "text", quiet=True,
                )
        assert exc.value.code == 1


class TestComparePartialFailure:
    @pytest.mark.asyncio
    async def test_one_model_fails_no_exit(self) -> None:
        """Um modelo falha mas o outro ok → não deve exit (success_count > 0)."""
        client = _make_client()
        ok = MagicMock()
        ok.error = None
        ok.eval_count = 3
        ok.total_duration_ns = 1_000_000_000
        ok.tokens_per_second = 3.0
        ok.model = "a"
        ok.response = "r"
        err = MagicMock()
        err.error = "falhou"
        err.model = "b"

        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._execute_model", new_callable=AsyncMock,
                   side_effect=[ok, err]), \
             patch("miru.commands.compare._render_comparison_table"), \
             patch("miru.commands.compare._render_seed_warning"):
            # não deve levantar SystemExit
            await _compare_async(
                ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                None, None, None, None, True, "text", quiet=True,
            )

    @pytest.mark.asyncio
    async def test_stream_mode_calls_render(self) -> None:
        """Stream mode (no_stream=False) com output text deve chamar render table."""
        client = _make_client()
        with patch("miru.commands.compare.OllamaClient", return_value=client), \
             patch("miru.commands.compare._execute_model", new_callable=AsyncMock,
                   side_effect=[TestCompareAsync._ok_result("a"), TestCompareAsync._ok_result("b")]), \
             patch("miru.commands.compare._render_comparison_table") as mock_table, \
             patch("miru.commands.compare._render_seed_warning"):
            await _compare_async(
                ["a", "b"], "prompt", None, "http://x", [], None, None, None,
                None, None, None, None, False, "text", quiet=True,
            )
        mock_table.assert_called_once()
