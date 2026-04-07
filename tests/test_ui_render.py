"""Tests for ui.render module."""

import io
from contextlib import redirect_stdout

import pytest

from miru.core.i18n import set_language
from miru.ui.render import (
    render_error,
    render_success,
    render_warning,
    render_info,
    render_model_table,
    render_metrics,
    render_table,
)


class TestRenderError:
    """Test render_error function."""

    def test_basic_error(self):
        """Test basic error rendering."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_error("Test error")
        result = output.getvalue()
        assert "✗" in result
        assert "Test error" in result

    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_error("Test error", "Try this solution")
        result = output.getvalue()
        assert "✗" in result
        assert "Test error" in result
        assert "Try this solution" in result

    def test_error_i18n_pt_br(self):
        """Test error with Portuguese i18n."""
        set_language("pt_BR")
        output = io.StringIO()
        with redirect_stdout(output):
            render_error("Modelo não encontrado")
        result = output.getvalue()
        assert "✗" in result

    def test_error_i18n_es_es(self):
        """Test error with Spanish i18n."""
        set_language("es_ES")
        output = io.StringIO()
        with redirect_stdout(output):
            render_error("Modelo no encontrado")
        result = output.getvalue()
        assert "✗" in result


class TestRenderSuccess:
    """Test render_success function."""

    def test_basic_success(self):
        """Test basic success rendering."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_success("Operation completed")
        result = output.getvalue()
        assert "✓" in result
        assert "Operation completed" in result


class TestRenderWarning:
    """Test render_warning function."""

    def test_basic_warning(self):
        """Test basic warning rendering."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_warning("This is a warning")
        result = output.getvalue()
        assert "⚠" in result
        assert "This is a warning" in result


class TestRenderInfo:
    """Test render_info function."""

    def test_basic_info(self):
        """Test basic info rendering."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_info("Processing file")
        result = output.getvalue()
        assert "ℹ" in result
        assert "Processing file" in result


class TestRenderModelTable:
    """Test render_model_table function."""

    def test_empty_models(self):
        """Test rendering empty model list."""
        set_language("en_US")
        output = io.StringIO()
        with redirect_stdout(output):
            render_model_table([])
        result = output.getvalue()
        # Should show "No models found" message
        assert "no models found" in result.lower()

    def test_single_model(self):
        """Test rendering single model."""
        models = [{"name": "gemma3:latest", "size": 1000000000, "modified_at": "2024-01-01"}]
        output = io.StringIO()
        with redirect_stdout(output):
            render_model_table(models)
        result = output.getvalue()
        assert "gemma3" in result

    def test_multiple_models(self):
        """Test rendering multiple models."""
        models = [
            {"name": "gemma3:latest", "size": 1000000000, "modified_at": "2024-01-01"},
            {"name": "qwen2.5:7b", "size": 5000000000, "modified_at": "2024-01-02"},
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            render_model_table(models)
        result = output.getvalue()
        assert "gemma3" in result
        assert "qwen2" in result

    def test_model_with_title(self):
        """Test rendering models with title."""
        models = [{"name": "test", "size": 100, "modified_at": ""}]
        output = io.StringIO()
        with redirect_stdout(output):
            render_model_table(models, title="Available Models")
        result = output.getvalue()
        assert "test" in result


class TestRenderMetrics:
    """Test render_metrics function."""

    def test_empty_metrics(self):
        """Test rendering empty metrics."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_metrics({})
        result = output.getvalue()
        # Should not output anything for empty metrics
        assert result == ""

    def test_basic_metrics(self):
        """Test rendering basic metrics."""
        chunk = {
            "eval_count": 100,
            "eval_duration": 1000000000,  # 1 second in nanoseconds
            "total_duration": 1500000000,
        }
        output = io.StringIO()
        with redirect_stdout(output):
            render_metrics(chunk, prefix="  ")
        result = output.getvalue()
        assert "100" in result
        assert "tok/s" in result

    def test_metrics_with_zero_duration(self):
        """Test metrics with zero duration."""
        chunk = {"eval_count": 100, "eval_duration": 0, "total_duration": 0}
        output = io.StringIO()
        with redirect_stdout(output):
            render_metrics(chunk)
        result = output.getvalue()
        # Should still show token count
        assert "100" in result


class TestRenderTable:
    """Test render_table function."""

    def test_empty_table(self):
        """Test rendering empty table."""
        output = io.StringIO()
        with redirect_stdout(output):
            render_table(["Name", "Value"], [])
        result = output.getvalue()
        # Should still show headers
        assert "Name" in result

    def test_table_with_rows(self):
        """Test rendering table with rows."""
        headers = ["Name", "Value"]
        rows = [["test1", "value1"], ["test2", "value2"]]
        output = io.StringIO()
        with redirect_stdout(output):
            render_table(headers, rows)
        result = output.getvalue()
        assert "test1" in result
        assert "value1" in result
        assert "test2" in result
        assert "value2" in result

    def test_table_with_title(self):
        """Test rendering table with title."""
        headers = ["Name", "Value"]
        rows = [["test", "value"]]
        output = io.StringIO()
        with redirect_stdout(output):
            render_table(headers, rows, title="Test Table")
        result = output.getvalue()
        assert "test" in result