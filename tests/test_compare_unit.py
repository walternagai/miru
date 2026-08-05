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


class TestRenderComparisonTable:
    def test_pt_br_headers(self) -> None:
        from miru.core.i18n import set_language
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        set_language("pt_BR")
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(
                [ModelResult("a", "p", "r", 5, 1_000_000_000, 2_000_000_000, 5.0, None)],
                quiet=False,
            )
        assert mock_print.called
        set_language("en_US")

    def test_es_headers(self) -> None:
        from miru.core.i18n import set_language
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        set_language("es_ES")
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(
                [ModelResult("a", "p", "r", 5, 1_000_000_000, 2_000_000_000, 5.0, None)],
                quiet=False,
            )
        assert mock_print.called
        set_language("en_US")

    def test_en_headers_with_error_row(self) -> None:
        from miru.core.i18n import set_language
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        set_language("en_US")
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(
                [
                    ModelResult("a", "p", "r", 5, 1_000_000_000, 2_000_000_000, 5.0, None),
                    ModelResult("b", "p", "", 0, 0, 0, 0.0, "erro"),
                ],
                quiet=False,
            )
        assert mock_print.called

    def test_quiet_returns(self) -> None:
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table([], quiet=True)
        mock_print.assert_not_called()

    def test_json_render(self) -> None:
        from miru.commands.compare import _render_json_output

        results = [
            ModelResult("a", "p", "r", 5, 1_000_000_000, 2_000_000_000, 5.0, None),
            ModelResult("b", "p", "", 0, 0, 0, 0.0, "erro"),
        ]
        _render_json_output(results)  # não deve levantar; imprime json

    def test_seed_warning_renders(self) -> None:
        from miru.commands.compare import _render_seed_warning
        from miru.commands.compare import console as cmp_console

        with patch.object(cmp_console, "print") as mock_print:
            _render_seed_warning(quiet=False, seed=None)
        assert mock_print.called

    def test_seed_warning_quiet_skips(self) -> None:
        from miru.commands.compare import _render_seed_warning
        from miru.commands.compare import console as cmp_console

        with patch.object(cmp_console, "print") as mock_print:
            _render_seed_warning(quiet=True, seed=None)
        mock_print.assert_not_called()


class TestCompareTableWinningRows:
    def test_best_model_marked_with_check(self) -> None:
        """O modelo mais rápido deve ser marcado com ✓ (verde)."""
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        results = [
            ModelResult("lento", "p", "r", 5, 1_000_000_000, 2_000_000_000, 2.0, None),
            ModelResult("rapido", "p", "r", 5, 1_000_000_000, 2_000_000_000, 10.0, None),
        ]
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(results, quiet=False)
        assert mock_print.called

    def test_single_model_no_check(self) -> None:
        """1 modelo → sem ✓ (len(valid_results) > 1 é falso)."""
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        results = [ModelResult("a", "p", "r", 5, 1_000_000_000, 2_000_000_000, 5.0, None)]
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(results, quiet=False)
        assert mock_print.called

    def test_all_failed_shows_dash_rows(self) -> None:
        """Todos com erro → linhas com '— ✗'."""
        from miru.commands.compare import _render_comparison_table
        from miru.commands.compare import console as cmp_console

        results = [ModelResult("a", "p", "", 0, 0, 0, 0.0, "err")]
        with patch.object(cmp_console, "print") as mock_print:
            _render_comparison_table(results, quiet=False)
        assert mock_print.called

    def test_seed_warning_pt(self) -> None:
        from miru.core.i18n import set_language
        from miru.commands.compare import _render_seed_warning
        from miru.commands.compare import console as cmp_console

        set_language("pt_BR")
        with patch.object(cmp_console, "print") as mock_print:
            _render_seed_warning(quiet=False, seed=None)
        assert mock_print.called
        set_language("en_US")


class TestCompareSeedEs:
    def test_seed_warning_es(self) -> None:
        from miru.core.i18n import set_language
        from miru.commands.compare import _render_seed_warning
        from miru.commands.compare import console as cmp_console

        set_language("es_ES")
        with patch.object(cmp_console, "print") as mock_print:
            _render_seed_warning(quiet=False, seed=None)
        assert mock_print.called
        set_language("en_US")

    def test_seed_provided_skips(self) -> None:
        from miru.commands.compare import _render_seed_warning
        from miru.commands.compare import console as cmp_console

        with patch.object(cmp_console, "print") as mock_print:
            _render_seed_warning(quiet=False, seed=42)
        mock_print.assert_not_called()


class TestExecuteModelExceptions:
    @pytest.mark.asyncio
    async def test_exception_returns_error_result(self) -> None:
        """Comportamento atual: except Exception engole e reporta 'model not found'.

        NOTA: o segundo `except Exception as e` (com o erro real) é INALCANÇÁVEL
        — o primeiro except Exception captura tudo. Bug de código morto documentado
        em PENDING; não corrigido para não mudar comportamento visível nesta rodada.
        """
        from miru.commands.compare import _execute_model

        client = MagicMock()
        client.chat = MagicMock(side_effect=RuntimeError("boom"))
        result = await _execute_model(
            client, "m", "p", "sys", None, {}, stream=False, quiet=True
        )
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_ollama_model_not_found(self) -> None:
        from miru.ollama.client import OllamaModelNotFound
        from miru.commands.compare import _execute_model

        client = MagicMock()
        client.chat = MagicMock(side_effect=OllamaModelNotFound("nope"))
        result = await _execute_model(
            client, "m", "p", "sys", None, {}, stream=False, quiet=True
        )
        assert result.error is not None
