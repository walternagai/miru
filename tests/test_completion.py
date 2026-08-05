"""Tests for miru/completion.py — shell completion generation."""

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestCompletion:
    def test_bash(self) -> None:
        result = runner.invoke(app, ["completion", "bash"])
        assert result.exit_code == 0
        assert "complete" in result.output

    def test_zsh(self) -> None:
        result = runner.invoke(app, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "#compdef" in result.output

    def test_fish(self) -> None:
        result = runner.invoke(app, ["completion", "fish"])
        assert result.exit_code == 0

    def test_unsupported_shell_exits(self) -> None:
        result = runner.invoke(app, ["completion", "powershell"])
        assert result.exit_code == 1

    def test_output_file(self, tmp_path) -> None:
        out = tmp_path / "sub" / "miru.bash"
        result = runner.invoke(app, ["completion", "bash", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert "complete" in out.read_text(encoding="utf-8")
