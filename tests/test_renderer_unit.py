"""Tests for miru/output/renderer.py — formatting and rendering helpers."""

from unittest.mock import MagicMock, patch

import pytest

from miru.output import renderer as r
from miru.output.renderer import (
    format_date,
    format_metrics,
    format_size,
    render_compare_header,
    render_empty_models,
    render_error,
    render_metrics,
    render_model_table,
    render_model_info,
    render_warning,
    _parse_parameters,
)


class TestFormatSize:
    def test_gb(self) -> None:
        assert format_size(5 * 1024**3) == "5.0 GB"

    def test_mb(self) -> None:
        assert format_size(512 * 1024**2) == "512 MB"

    def test_kb(self) -> None:
        assert format_size(1536) == "1.5 KB"

    def test_bytes(self) -> None:
        assert format_size(500) == "500 B"


class TestFormatDate:
    def test_empty(self) -> None:
        assert format_date("") == "-"

    def test_iso_with_t(self) -> None:
        assert format_date("2026-04-01T12:00:00Z") == "2026-04-01"

    def test_date_only(self) -> None:
        assert format_date("2026-04-01") == "2026-04-01"


class TestFormatMetrics:
    def test_with_speed(self) -> None:
        chunk = {"eval_count": 10, "eval_duration": 1_000_000_000, "total_duration": 2_000_000_000}
        out = format_metrics(chunk)
        assert "10" in out
        assert "10.0" in out  # tokens/s

    def test_no_speed_when_no_duration(self) -> None:
        chunk = {"eval_count": 5, "total_duration": 0}
        out = format_metrics(chunk)
        assert "5" in out
        assert "tokens" in out


class TestRenderMetrics:
    def test_quiet_does_nothing(self, capsys) -> None:
        render_metrics({"eval_count": 1}, quiet=True)
        assert capsys.readouterr().out == ""

    def test_prints_metrics(self, capsys) -> None:
        render_metrics({"eval_count": 3, "total_duration": 1_000_000_000})
        assert "✓" in capsys.readouterr().out


class TestRenderErrorWarning:
    def test_render_error(self) -> None:
        with patch.object(r, "console_stderr") as mock_console:
            render_error("msg", "hint")
        printed = mock_console.print.call_args_list
        assert any("msg" in str(call) for call in printed)
        assert any("hint" in str(call) for call in printed)

    def test_render_warning(self) -> None:
        with patch.object(r, "console_stderr") as mock_console:
            render_warning("warn")
        assert "warn" in str(mock_console.print.call_args)


class TestRenderEmptyModels:
    def test_prints_message(self) -> None:
        with patch.object(r, "console") as mock_console:
            render_empty_models()
        assert mock_console.print.call_count >= 1


class TestRenderModelTable:
    def test_empty_models(self) -> None:
        with patch.object(r, "console") as mock_console:
            render_model_table([])
        assert mock_console.print.call_count >= 1

    def test_models_table(self) -> None:
        models = [{"name": "gemma3:latest", "size": 5 * 1024**3, "modified_at": "2026-04-01T00:00:00Z"}]
        with patch.object(r, "console") as mock_console:
            render_model_table(models)
        assert mock_console.print.call_count >= 1


class TestRenderModelInfo:
    def test_quiet_prints_name(self, capsys) -> None:
        render_model_info("llava", {}, {}, quiet=True)
        assert "llava" in capsys.readouterr().out

    def test_panel_with_capabilities(self) -> None:
        data = {
            "details": {"families": ["llama", "clip"], "parameter_size": "7B",
                        "quantization_level": "Q4_K_M"},
            "parameters": "",
        }
        caps = {"supports_vision": True, "capabilities": ["tools", "vision"],
                "max_context": 4096}
        with patch.object(r, "console") as mock_console:
            render_model_info("llava", data, caps)
        assert mock_console.print.call_count == 1

    def test_parameters_parsed_and_displayed(self) -> None:
        data = {"details": {}, "parameters": "temperature\t0.8\nnum_ctx\t4096\n"}
        with patch.object(r, "console") as mock_console:
            render_model_info("m", data, {"max_context": 2048})
        assert mock_console.print.call_count == 1


class TestParseParameters:
    def test_parses_tab_separated(self) -> None:
        assert _parse_parameters("a\t1\nb\t2\n") == {"a": "1", "b": "2"}

    def test_skips_lines_without_tab(self) -> None:
        assert _parse_parameters("no-tab\nk\tv\n") == {"k": "v"}


class TestRenderCompareHeader:
    def test_header(self, capsys) -> None:
        with patch.object(r, "console") as mock_console:
            render_compare_header("gemma3", 1, 2)
        assert mock_console.print.call_count >= 1
