"""Tests for miru/commands/batch.py rendering helpers."""

import json

from unittest.mock import patch

import pytest

from miru.commands.batch import (
    BatchResult,
    _render_results_json,
    _render_results_jsonl,
    _render_results_table,
)
from miru.output import renderer as r


def _results():
    return [
        BatchResult("p1", "r1", True, eval_count=5, total_duration_ns=1_000_000_000, tokens_per_second=5.0),
        BatchResult("p2", "", False, error="boom"),
    ]


class TestRenderResultsTable:
    def test_quiet_no_output(self, capsys) -> None:
        _render_results_table(_results(), quiet=True)
        assert capsys.readouterr().out == ""

    def test_table_with_results(self) -> None:
        import miru.commands.batch as batch_mod

        with patch.object(batch_mod, "console") as mock_console:
            _render_results_table(_results(), quiet=False)
        assert mock_console.print.call_count >= 2  # table + summary


class TestRenderResultsJson:
    def test_structure(self, capsys) -> None:
        _render_results_json(_results(), "gemma3")
        data = json.loads(capsys.readouterr().out)
        assert data["model"] == "gemma3"
        assert data["total"] == 2
        assert data["success_count"] == 1
        assert data["error_count"] == 1
        assert data["results"][0]["metrics"]["eval_count"] == 5
        assert data["results"][1]["metrics"] is None


class TestRenderResultsJsonl:
    def test_lines(self, capsys) -> None:
        _render_results_jsonl(_results())
        lines = capsys.readouterr().out.strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["success"] is True
        assert second["success"] is False
        assert second["error"] == "boom"
