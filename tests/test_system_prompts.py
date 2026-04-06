"""Tests for system prompt functionality."""

from typer.testing import CliRunner

from miru.cli import app

runner = CliRunner()


class TestSystemPromptFlags:
    """Tests for system prompt flag acceptance."""

    def test_run_accepts_system_flag(self) -> None:
        """Should accept --system flag in run command."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "--system" in result.output
        assert "--system-file" in result.output

    def test_chat_accepts_system_flag(self) -> None:
        """Should accept --system flag in chat command."""
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "--system" in result.output
        assert "--system-file" in result.output

    def test_compare_accepts_system_flag(self) -> None:
        """Should accept --system flag in compare command."""
        result = runner.invoke(app, ["compare", "--help"])
        assert result.exit_code == 0
        assert "--system" in result.output
        assert "--system-file" in result.output

    def test_compare_rejects_both_system_and_system_file(self) -> None:
        """Should error when both --system and --system-file are provided."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("System prompt")
            f.flush()

            try:
                result = runner.invoke(
                    app,
                    [
                        "compare",
                        "model1",
                        "model2",
                        "--prompt",
                        "Test",
                        "--system",
                        "Direct",
                        "--system-file",
                        f.name,
                    ],
                )
                # Should show error about using both flags
                assert result.exit_code == 1 or "não ambos" in result.output
            finally:
                Path(f.name).unlink()
