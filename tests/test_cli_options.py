"""Tests for miru/cli_options.py — CLI option helpers."""

import pytest


class TestGetModelWithFallback:
    def test_model_provided(self) -> None:
        from miru.cli_options import get_model_with_fallback

        assert get_model_with_fallback("gemma3") == "gemma3"

    def test_fallback_to_config(self, monkeypatch) -> None:
        from miru.cli_options import get_model_with_fallback

        monkeypatch.setattr("miru.core.config.resolve_model", lambda: "llama3")
        assert get_model_with_fallback(None) == "llama3"

    def test_no_model_exits(self, monkeypatch) -> None:
        from miru.cli_options import get_model_with_fallback

        monkeypatch.setattr("miru.core.config.resolve_model", lambda: None)
        with pytest.raises(SystemExit) as exc:
            get_model_with_fallback(None)
        assert exc.value.code == 1
