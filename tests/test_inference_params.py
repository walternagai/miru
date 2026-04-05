"""Tests for inference_params module."""

import pytest

from miru.inference_params import build_options


class TestBuildOptions:
    """Tests for build_options function."""

    def test_all_none_returns_none(self):
        """All None parameters should return None."""
        result = build_options(
            temperature=None,
            top_p=None,
            top_k=None,
            max_tokens=None,
            seed=None,
            repeat_penalty=None,
            ctx=None,
        )
        assert result is None

    def test_single_temperature(self):
        """Single parameter should return dict with that parameter."""
        result = build_options(
            temperature=0.7,
            top_p=None,
            top_k=None,
            max_tokens=None,
            seed=None,
            repeat_penalty=None,
            ctx=None,
        )
        assert result == {"temperature": 0.7}

    def test_max_tokens_mapping_to_num_predict(self):
        """max_tokens should be mapped to num_predict."""
        result = build_options(
            temperature=None,
            top_p=None,
            top_k=None,
            max_tokens=512,
            seed=None,
            repeat_penalty=None,
            ctx=None,
        )
        assert result == {"num_predict": 512}
        assert "max_tokens" not in result

    def test_ctx_mapping_to_num_ctx(self):
        """ctx should be mapped to num_ctx."""
        result = build_options(
            temperature=None,
            top_p=None,
            top_k=None,
            max_tokens=None,
            seed=None,
            repeat_penalty=None,
            ctx=4096,
        )
        assert result == {"num_ctx": 4096}
        assert "ctx" not in result

    def test_multiple_parameters(self):
        """Multiple parameters should all be included."""
        result = build_options(
            temperature=0.8,
            top_p=0.95,
            top_k=40,
            max_tokens=1000,
            seed=42,
            repeat_penalty=1.1,
            ctx=8192,
        )
        expected = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 40,
            "num_predict": 1000,
            "seed": 42,
            "repeat_penalty": 1.1,
            "num_ctx": 8192,
        }
        assert result == expected

    def test_temperature_and_max_tokens(self):
        """Temperature and max_tokens combination."""
        result = build_options(
            temperature=0.7,
            top_p=None,
            top_k=None,
            max_tokens=200,
            seed=None,
            repeat_penalty=None,
            ctx=None,
        )
        assert result == {"temperature": 0.7, "num_predict": 200}

    def test_zero_values_included(self):
        """Zero values should be included (not treated as None)."""
        result = build_options(
            temperature=0.0,
            top_p=0.0,
            top_k=0,
            max_tokens=0,
            seed=0,
            repeat_penalty=0.0,
            ctx=0,
        )
        assert result is not None
        assert len(result) == 7
        assert result["temperature"] == 0.0
        assert result["top_p"] == 0.0
        assert result["top_k"] == 0
        assert result["num_predict"] == 0
        assert result["seed"] == 0
        assert result["repeat_penalty"] == 0.0
        assert result["num_ctx"] == 0

    def test_repeat_penalty_unchanged_name(self):
        """repeat_penalty should keep same name in API."""
        result = build_options(
            temperature=None,
            top_p=None,
            top_k=None,
            max_tokens=None,
            seed=None,
            repeat_penalty=1.2,
            ctx=None,
        )
        assert result == {"repeat_penalty": 1.2}

    def test_all_standard_params_unchanged_names(self):
        """temperature, top_p, top_k, seed should keep same names."""
        result = build_options(
            temperature=1.5,
            top_p=0.9,
            top_k=50,
            max_tokens=None,
            seed=123,
            repeat_penalty=None,
            ctx=None,
        )
        assert result["temperature"] == 1.5
        assert result["top_p"] == 0.9
        assert result["top_k"] == 50
        assert result["seed"] == 123