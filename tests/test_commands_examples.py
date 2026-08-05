"""Tests for miru/commands/examples.py — example listing and showing."""

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestExamplesCmd:
    def test_list_all(self) -> None:
        result = runner.invoke(app, ["examples", "--list"])
        assert result.exit_code == 0

    def test_no_match_filter(self) -> None:
        result = runner.invoke(app, ["examples", "--list", "--category", "zzz-nonexistent"])
        assert result.exit_code == 0

    def test_filter_by_category(self) -> None:
        result = runner.invoke(app, ["examples", "--list", "--category", "basics"])
        assert result.exit_code == 0

    def test_filter_by_tag(self) -> None:
        result = runner.invoke(app, ["examples", "--list", "--tag", "chat"])
        assert result.exit_code == 0

    def test_show_existing(self) -> None:
        result = runner.invoke(app, ["examples", "hello-world"])
        assert result.exit_code == 0
        assert "hello-world" in result.output or "Hello" in result.output

    def test_show_missing_exits(self) -> None:
        result = runner.invoke(app, ["examples", "nao_existe"])
        assert result.exit_code == 1

    def test_show_with_copy_without_pyperclip(self) -> None:
        result = runner.invoke(app, ["examples", "hello-world", "--copy"])
        assert result.exit_code == 0

    def test_categories(self) -> None:
        result = runner.invoke(app, ["examples", "--categories"])
        assert result.exit_code == 0


class TestExamplesCopyInstalled:
    def test_copy_with_pyperclip(self) -> None:
        """pyperclip instalado (mock) → copia e confirma."""
        from unittest.mock import MagicMock, patch

        fake_pyperclip = MagicMock()
        with patch.dict("sys.modules", {"pyperclip": fake_pyperclip}):
            result = runner.invoke(app, ["examples", "hello-world", "--copy"])
        assert result.exit_code == 0
        fake_pyperclip.copy.assert_called_once()


class TestExamplesNoArgs:
    def test_no_args_shows_browser(self) -> None:
        """Sem args → browser interativo (lista popular)."""
        result = runner.invoke(app, ["examples"])
        assert result.exit_code == 0
        assert "hello-world" in result.output
