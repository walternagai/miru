"""Tests for miru/commands/compare.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from miru.cli import app
from miru.commands.compare import ModelResult, _calculate_tokens_per_second

runner = CliRunner()


class TestCalculateTokensPerSecond:
    """Tests for _calculate_tokens_per_second function."""

    def test_normal_calculation(self) -> None:
        """Should calculate tokens per second correctly."""
        eval_count = 100
        eval_duration_ns = 5_000_000_000
        
        result = _calculate_tokens_per_second(eval_count, eval_duration_ns)
        
        assert result == 20.0

    def test_zero_duration(self) -> None:
        """Should return 0 when eval_duration is 0."""
        result = _calculate_tokens_per_second(100, 0)
        assert result == 0.0

    def test_zero_tokens(self) -> None:
        """Should return 0 when eval_count is 0."""
        result = _calculate_tokens_per_second(0, 5_000_000_000)
        assert result == 0.0

    def test_fractional_result(self) -> None:
        """Should handle fractional results."""
        result = _calculate_tokens_per_second(47, 2_300_000_000)
        assert abs(result - 20.43478) < 0.001


class TestModelResult:
    """Tests for ModelResult dataclass."""

    def test_successful_result(self) -> None:
        """Should create successful result."""
        result = ModelResult(
            model="gemma3:latest",
            prompt="Hello",
            response="Hi there!",
            eval_count=10,
            eval_duration_ns=1_000_000_000,
            total_duration_ns=1_100_000_000,
            tokens_per_second=10.0,
            error=None,
        )
        
        assert result.model == "gemma3:latest"
        assert result.response == "Hi there!"
        assert result.eval_count == 10
        assert result.error is None

    def test_error_result(self) -> None:
        """Should create error result."""
        result = ModelResult(
            model="fake:model",
            prompt="Hello",
            response="",
            eval_count=0,
            eval_duration_ns=0,
            total_duration_ns=0,
            tokens_per_second=0.0,
            error='Modelo "fake:model" não encontrado.',
        )
        
        assert result.model == "fake:model"
        assert result.response == ""
        assert result.error == 'Modelo "fake:model" não encontrado.'


class TestCompareCommand:
    """Tests for miru compare command."""

    def test_compare_requires_at_least_two_models(self) -> None:
        """Should fail if only one model is provided."""
        result = runner.invoke(app, ["compare", "gemma3:latest", "--prompt", "Hello"])
        assert result.exit_code == 1
        assert "Compare requer ao menos 2 modelos" in result.output

    def test_compare_requires_prompt_or_file(self) -> None:
        """Should fail if no prompt is provided."""
        result = runner.invoke(app, ["compare", "gemma3", "qwen2.5:7b"])
        assert result.exit_code == 1
        assert "É necessário fornecer --prompt ou --prompt-file" in result.output

    def test_compare_rejects_both_prompt_and_file(self) -> None:
        """Should fail if both --prompt and --prompt-file are provided."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--prompt-file",
                "/tmp/prompt.txt",
            ],
        )
        assert result.exit_code == 1
        assert "Use --prompt OU --prompt-file" in result.output

    def test_compare_invalid_format(self) -> None:
        """Should reject invalid format."""
        result = runner.invoke(
            app,
            ["compare", "gemma3", "qwen2.5:7b", "--prompt", "Hello", "--format", "xml"],
        )
        assert result.exit_code == 1
        assert "Formato inválido" in result.output

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_basic_execution(self, mock_compare: AsyncMock) -> None:
        """Should call compare with correct parameters."""
        result = runner.invoke(
            app,
            ["compare", "gemma3:latest", "qwen2.5:7b", "--prompt", "Test prompt"],
        )
        
        assert result.exit_code == 0
        mock_compare.assert_called_once()

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_with_seed(self, mock_compare: AsyncMock) -> None:
        """Should pass seed parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3:latest",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--seed",
                "42",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["seed"] == 42

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_with_temperature(self, mock_compare: AsyncMock) -> None:
        """Should pass temperature parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3:latest",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--temperature",
                "0.7",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_json_format(self, mock_compare: AsyncMock) -> None:
        """Should pass format parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3:latest",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--format",
                "json",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["output_format"] == "json"

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_no_stream(self, mock_compare: AsyncMock) -> None:
        """Should pass no_stream parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3:latest",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--no-stream",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["no_stream"] is True

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_quiet_mode(self, mock_compare: AsyncMock) -> None:
        """Should pass quiet parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3:latest",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--quiet",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["quiet"] is True

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_with_image(self, mock_compare: AsyncMock) -> None:
        """Should pass image parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "llava:latest",
                "moondream:latest",
                "--prompt",
                "Describe",
                "--image",
                "test.png",
            ],
        )
        
        assert result.exit_code == 0
        call_kwargs = mock_compare.call_args[1]
        assert "test.png" in call_kwargs["images"]

    def test_compare_rejects_file_parameter(self) -> None:
        """Should reject --file parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--file",
                "test.txt",
            ],
        )
        assert result.exit_code == 1
        assert "--file e --audio não são suportados" in result.output

    def test_compare_rejects_audio_parameter(self) -> None:
        """Should reject --audio parameter."""
        result = runner.invoke(
            app,
            [
                "compare",
                "gemma3",
                "qwen2.5:7b",
                "--prompt",
                "Hello",
                "--audio",
                "test.mp3",
            ],
        )
        assert result.exit_code == 1
        assert "--file e --audio não são suportados" in result.output


class TestCompareIntegration:
    """Integration tests for compare command."""

    @patch("miru.commands.compare._compare_async", new_callable=AsyncMock)
    def test_compare_successful_execution(self, mock_compare: AsyncMock) -> None:
        """Should execute comparison successfully with mocked async function."""
        mock_compare.return_value = None
        
        result = runner.invoke(
            app,
            ["compare", "gemma3:latest", "qwen2.5:7b", "--prompt", "Hello"],
        )
        
        assert result.exit_code == 0

    def test_compare_json_output(self) -> None:
        """Should output valid JSON in json format."""
        with patch("miru.commands.compare._compare_async", new_callable=AsyncMock) as mock_compare:
            results = [
                ModelResult(
                    model="gemma3:latest",
                    prompt="Hello",
                    response="Hi!",
                    eval_count=10,
                    eval_duration_ns=1_000_000_000,
                    total_duration_ns=1_100_000_000,
                    tokens_per_second=10.0,
                    error=None,
                ),
                ModelResult(
                    model="qwen2.5:7b",
                    prompt="Hello",
                    response="Hello!",
                    eval_count=8,
                    eval_duration_ns=800_000_000,
                    total_duration_ns=900_000_000,
                    tokens_per_second=10.0,
                    error=None,
                ),
            ]
            
            mock_compare.return_value = None
            
            result = runner.invoke(
                app,
                [
                    "compare",
                    "gemma3:latest",
                    "qwen2.5:7b",
                    "--prompt",
                    "Hello",
                    "--format",
                    "json",
                    "--quiet",
                ],
            )
            
            assert result.exit_code == 0