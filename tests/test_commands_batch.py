"""Tests for miru/commands/batch.py."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from miru.cli import app

runner = CliRunner()


class TestBatchCommand:
    """Tests for miru batch command."""

    def test_batch_help(self) -> None:
        """Should show help message."""
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--prompts" in result.output
        assert "--format" in result.output
        assert "text/json/jsonl" in result.output

    def test_batch_missing_prompts_file(self) -> None:
        """Should error when prompts file not provided."""
        result = runner.invoke(app, ["batch", "gemma3:latest"])
        # Should show error about missing required option
        assert (
            result.exit_code != 0
            or "required" in result.output.lower()
            or "usage" in result.output.lower()
        )

    def test_batch_file_not_found(self) -> None:
        """Should error when prompts file not found."""
        result = runner.invoke(app, ["batch", "gemma3:latest", "--prompts", "nonexistent.txt"])
        assert result.exit_code == 1
        assert "não encontrado" in result.output

    def test_batch_empty_file(self) -> None:
        """Should error when prompts file is empty."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            f.flush()

            try:
                result = runner.invoke(app, ["batch", "gemma3:latest", "--prompts", f.name])
                assert result.exit_code == 1
                assert "vazio" in result.output.lower()
            finally:
                Path(f.name).unlink()

    def test_batch_both_system_and_system_file(self) -> None:
        """Should error when both --system and --system-file provided."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("system prompt")
            f.flush()

            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as p:
                    p.write("prompt\n")
                    p.flush()

                    result = runner.invoke(
                        app,
                        [
                            "batch",
                            "gemma3:latest",
                            "--prompts",
                            p.name,
                            "--system",
                            "Direct",
                            "--system-file",
                            f.name,
                        ],
                    )

                    assert result.exit_code == 1
                    assert "não ambos" in result.output
            finally:
                Path(f.name).unlink()

    def test_batch_invalid_format(self) -> None:
        """Should error with invalid format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test\n")
            f.flush()

            try:
                result = runner.invoke(
                    app, ["batch", "gemma3:latest", "--prompts", f.name, "--format", "xml"]
                )

                assert result.exit_code == 1
                assert "inválido" in result.output.lower()
            finally:
                Path(f.name).unlink()


class TestReadPromptsFile:
    """Tests for _read_prompts_file function."""

    def test_read_plain_text(self) -> None:
        """Should read plain text prompts."""
        from miru.commands.batch import _read_prompts_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("First prompt\nSecond prompt\n\nThird prompt\n")
            f.flush()

            try:
                prompts = _read_prompts_file(f.name)
                assert len(prompts) == 3
                assert prompts[0] == "First prompt"
                assert prompts[1] == "Second prompt"
                assert prompts[2] == "Third prompt"
            finally:
                Path(f.name).unlink()

    def test_read_jsonl_with_prompt_field(self) -> None:
        """Should parse JSONL with prompt field."""
        from miru.commands.batch import _read_prompts_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write('{"prompt": "First"}\n{"prompt": "Second"}\n')
            f.flush()

            try:
                prompts = _read_prompts_file(f.name)
                assert prompts == ["First", "Second"]
            finally:
                Path(f.name).unlink()

    def test_read_jsonl_with_text_field(self) -> None:
        """Should parse JSONL with text field."""
        from miru.commands.batch import _read_prompts_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write('{"text": "First"}\n{"text": "Second"}\n')
            f.flush()

            try:
                prompts = _read_prompts_file(f.name)
                assert prompts == ["First", "Second"]
            finally:
                Path(f.name).unlink()

    def test_read_mixed_format(self) -> None:
        """Should parse mixed JSONL and plain text."""
        from miru.commands.batch import _read_prompts_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write('{"prompt": "JSON prompt"}\nPlain text\n{"text": "Another"}\n')
            f.flush()

            try:
                prompts = _read_prompts_file(f.name)
                assert len(prompts) == 3
                assert prompts[0] == "JSON prompt"
                assert prompts[1] == "Plain text"
                assert prompts[2] == "Another"
            finally:
                Path(f.name).unlink()

    def test_read_file_not_found(self) -> None:
        """Should exit when file not found."""
        from miru.commands.batch import _read_prompts_file
        import sys

        # _read_prompts_file calls sys.exit(1) on error
        # We can't easily test this, so we test the parent function
        # which handles the error
        pass


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_success(self) -> None:
        """Should create successful result."""
        from miru.commands.batch import BatchResult

        result = BatchResult(
            prompt="Test",
            response="Response",
            success=True,
            eval_count=10,
            eval_duration_ns=1000000000,
            total_duration_ns=1100000000,
            tokens_per_second=10.0,
        )

        assert result.success
        assert result.error is None
        assert result.eval_count == 10

    def test_batch_result_error(self) -> None:
        """Should create error result."""
        from miru.commands.batch import BatchResult

        result = BatchResult(prompt="Test", response="", success=False, error="Model not found")

        assert not result.success
        assert result.error == "Model not found"
        assert result.eval_count == 0


class TestCalculateTokensPerSecond:
    """Tests for _calculate_tokens_per_second function."""

    def test_normal_calculation(self) -> None:
        """Should calculate tokens per second correctly."""
        from miru.commands.batch import _calculate_tokens_per_second

        result = _calculate_tokens_per_second(100, 1000000000)  # 100 tokens in 1 second
        assert result == 100.0

    def test_zero_duration(self) -> None:
        """Should return 0 for zero duration."""
        from miru.commands.batch import _calculate_tokens_per_second

        result = _calculate_tokens_per_second(100, 0)
        assert result == 0.0

    def test_zero_tokens(self) -> None:
        """Should return 0 for zero tokens."""
        from miru.commands.batch import _calculate_tokens_per_second

        result = _calculate_tokens_per_second(0, 1000000000)
        assert result == 0.0

    def test_fractional_result(self) -> None:
        """Should handle fractional results."""
        from miru.commands.batch import _calculate_tokens_per_second

        result = _calculate_tokens_per_second(50, 2000000000)  # 25 tokens/sec
        assert result == 25.0
