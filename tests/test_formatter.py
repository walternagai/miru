"""Tests for miru/output/formatter.py."""

import json
from unittest.mock import MagicMock

import pytest

from miru.output.formatter import (
    _format_size,
    models_to_json,
    print_json,
    print_plain,
    result_to_json,
    to_json,
)


class TestToJson:
    """Tests for to_json function."""

    def test_to_json_basic(self) -> None:
        """Should serialize dict to JSON."""
        data = {"name": "test", "value": 42}
        result = to_json(data)
        
        assert '"name": "test"' in result
        assert '"value": 42' in result
    
    def test_to_json_with_indent(self) -> None:
        """Should use custom indent."""
        data = {"name": "test"}
        result = to_json(data, indent=4)
        
        assert '{\n    "name": "test"\n}' == result
    
    def test_to_json_ensure_ascii_false(self) -> None:
        """Should preserve UTF-8 characters."""
        data = {"nome": "José"}
        result = to_json(data)
        
        assert "José" in result
        assert "\\u" not in result
    
    def test_to_json_list(self) -> None:
        """Should serialize list."""
        data = [{"name": "a"}, {"name": "b"}]
        result = to_json(data)
        
        parsed = json.loads(result)
        assert len(parsed) == 2


class TestPrintJson:
    """Tests for print_json function."""

    def test_print_json_output(self, capsys) -> None:
        """Should print JSON to stdout."""
        data = {"name": "test", "value": 123}
        print_json(data)
        captured = capsys.readouterr()
        
        assert "name" in captured.out
        assert "test" in captured.out
        assert "\n" in captured.out
    
    def test_print_json_utf8(self, capsys) -> None:
        """Should preserve UTF-8 characters."""
        data = {"nome": "José"}
        print_json(data)
        captured = capsys.readouterr()
        
        assert "José" in captured.out


class TestModelsToJson:
    """Tests for models_to_json function."""

    def test_models_to_json_adds_size_human(self) -> None:
        """Should add size_human field."""
        models = [
            {"name": "gemma3:latest", "size": 5_368_709_120},
            {"name": "qwen2.5:7b", "size": 524_288_000},
        ]
        
        result = models_to_json(models)
        
        assert len(result) == 2
        assert result[0]["size_human"] == "5.0 GB"
        assert result[1]["size_human"] == "500 MB"
        assert result[0]["name"] == "gemma3:latest"
    
    def test_models_to_json_doesnt_modify_original(self) -> None:
        """Should not modify original list."""
        models = [{"name": "test", "size": 1024}]
        original = list(models)
        
        models_to_json(models)
        
        assert "size_human" not in models[0]
    
    def test_models_to_json_zero_size(self) -> None:
        """Should handle zero size."""
        models = [{"name": "test", "size": 0}]
        
        result = models_to_json(models)
        
        assert result[0]["size_human"] == "0 B"


class TestResultToJson:
    """Tests for result_to_json function."""

    def test_result_to_json_success(self) -> None:
        """Should convert successful result."""
        result = MagicMock()
        result.model = "gemma3:latest"
        result.prompt = "Hello"
        result.response = "Hi there"
        result.eval_count = 10
        result.eval_duration_ns = 1_000_000_000
        result.total_duration_ns = 1_100_000_000
        result.tokens_per_second = 10.0
        result.error = None
        
        output = result_to_json(result)
        
        assert output["model"] == "gemma3:latest"
        assert output["prompt"] == "Hello"
        assert output["response"] == "Hi there"
        assert output["metrics"]["eval_count"] == 10
        assert output["metrics"]["tokens_per_second"] == 10.0
        assert output["error"] is None
    
    def test_result_to_json_with_error(self) -> None:
        """Should convert result with error."""
        result = MagicMock()
        result.model = "fake:model"
        result.prompt = "Test"
        result.response = ""
        result.error = "Model not found"
        
        output = result_to_json(result)
        
        assert output["model"] == "fake:model"
        assert output["metrics"] is None
        assert output["error"] == "Model not found"
    
    def test_result_to_json_rounds_tokens_per_second(self) -> None:
        """Should round tokens_per_second to 1 decimal."""
        result = MagicMock()
        result.model = "test"
        result.prompt = "test"
        result.response = "test"
        result.eval_count = 47
        result.eval_duration_ns = 2_300_000_000
        result.total_duration_ns = 2_350_000_000
        result.tokens_per_second = 20.43478
        result.error = None
        
        output = result_to_json(result)
        
        assert output["metrics"]["tokens_per_second"] == 20.4


class TestPrintPlain:
    """Tests for print_plain function."""

    def test_print_plain_output(self, capsys) -> None:
        """Should print plain text."""
        print_plain("Hello world")
        captured = capsys.readouterr()
        
        assert captured.out == "Hello world\n"
    
    def test_print_plain_multiline(self, capsys) -> None:
        """Should handle multiline text."""
        print_plain("Line 1\nLine 2")
        captured = capsys.readouterr()
        
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out


class TestFormatSizePrivate:
    """Tests for _format_size private function."""

    def test_format_gb(self) -> None:
        """Should format GB."""
        assert _format_size(5_368_709_120) == "5.0 GB"
    
    def test_format_mb(self) -> None:
        """Should format MB."""
        assert _format_size(524_288_000) == "500 MB"
    
    def test_format_kb(self) -> None:
        """Should format KB."""
        assert _format_size(51_200) == "50.0 KB"
    
    def test_format_bytes(self) -> None:
        """Should format bytes."""
        assert _format_size(512) == "512 B"
    
    def test_format_exact_mb(self) -> None:
        """Should format exact MB without decimal."""
        assert _format_size(1_048_576) == "1 MB"