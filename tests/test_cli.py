"""Tests for miru/cli.py."""

from typer.testing import CliRunner

from miru.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version_command(self) -> None:
        """Should display version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "miru" in result.output

    def test_help_flag(self) -> None:
        """Should display help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "CLI Python para servidor Ollama" in result.output

    def test_list_help(self) -> None:
        """Should display list command help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List available models" in result.output

    def test_info_help(self) -> None:
        """Should display info command help."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "Show detailed information" in result.output

    def test_pull_help(self) -> None:
        """Should display pull command help."""
        result = runner.invoke(app, ["pull", "--help"])
        assert result.exit_code == 0
        assert "Download a model" in result.output