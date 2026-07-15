"""Tests for core.i18n module."""

import pytest
from miru.core.i18n import (
    t,
    set_language,
    get_language,
    detect_language,
    init_i18n,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    MESSAGES,
)


class TestI18nBasics:
    """Test basic i18n functionality."""

    def test_supported_languages(self):
        """Test that supported languages are defined."""
        assert "pt_BR" in SUPPORTED_LANGUAGES
        assert "en_US" in SUPPORTED_LANGUAGES
        assert "es_ES" in SUPPORTED_LANGUAGES

    def test_default_language(self):
        """Test that default language is en_US."""
        assert DEFAULT_LANGUAGE == "en_US"

    def test_messages_exist(self):
        """Test that messages are defined."""
        assert "en_US" in MESSAGES
        assert "pt_BR" in MESSAGES
        assert "es_ES" in MESSAGES

    def test_init_i18n(self):
        """Test that init_i18n works."""
        init_i18n()
        # Should not raise
        assert get_language() in SUPPORTED_LANGUAGES


class TestLanguageSelection:
    """Test language selection functions."""

    def test_set_language_pt_br(self):
        """Test setting language to pt_BR."""
        set_language("pt_BR")
        assert get_language() == "pt_BR"

    def test_set_language_en_us(self):
        """Test setting language to en_US."""
        set_language("en_US")
        assert get_language() == "en_US"

    def test_set_language_es_es(self):
        """Test setting language to es_ES."""
        set_language("es_ES")
        assert get_language() == "es_ES"

    def test_set_language_invalid(self):
        """Test setting invalid language falls back to default."""
        set_language("invalid")
        assert get_language() == DEFAULT_LANGUAGE


class TestTranslation:
    """Test translation function."""

    def test_translate_simple_key(self):
        """Test translating a simple key."""
        set_language("en_US")
        msg = t("error.model_not_found", model="test")
        assert "test" in msg
        assert "not found" in msg.lower()

    def test_translate_pt_br(self):
        """Test Portuguese translation."""
        set_language("pt_BR")
        msg = t("error.model_not_found", model="teste")
        assert "teste" in msg
        assert "não encontrado" in msg.lower()

    def test_translate_es_es(self):
        """Test Spanish translation."""
        set_language("es_ES")
        msg = t("error.model_not_found", model="prueba")
        assert "prueba" in msg
        assert "no encontrado" in msg.lower()

    def test_translate_missing_key(self):
        """Test that missing key returns the key itself."""
        msg = t("nonexistent.key")
        assert msg == "nonexistent.key"

    def test_translate_with_multiple_params(self):
        """Test translation with multiple parameters."""
        set_language("en_US")
        msg = t("chat.session_ended", turns=5, model="gemma3")
        assert "5" in msg
        assert "gemma3" in msg

    def test_translate_with_same_param_name(self):
        """Test that t() works when local variable has same name as kwarg."""
        set_language("en_US")
        # This was a bug - the function parameter 'key' conflicted with 'key=key'
        key = "test_key"
        value = "test_value"
        msg = t("config.key_set", key=key, value=value)
        assert "test_key" in msg
        assert "test_value" in msg

    def test_translate_fallback_to_default(self):
        """Test that unknown language falls back to default."""
        set_language("fr_FR")  # Not supported
        msg = t("error.model_not_found", model="test")
        # Should use default (en_US)
        assert "not found" in msg.lower()


class TestDetectLanguage:
    """Test language detection."""

    def test_detect_from_env(self, monkeypatch):
        """Test detection from MIRU_LANG env var."""
        monkeypatch.setenv("MIRU_LANG", "pt_BR")
        lang = detect_language()
        assert lang == "pt_BR"

    def test_detect_from_lang_env(self, monkeypatch):
        """Test detection from LANG env var."""
        monkeypatch.delenv("MIRU_LANG", raising=False)
        monkeypatch.setenv("LANG", "pt_BR.UTF-8")
        lang = detect_language()
        assert lang == "pt_BR"

    def test_detect_default(self, monkeypatch):
        """Test default when no env vars set."""
        monkeypatch.delenv("MIRU_LANG", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        lang = detect_language()
        # Should return default or detected from system
        assert lang in SUPPORTED_LANGUAGES or lang == DEFAULT_LANGUAGE


class TestMessageCategories:
    """Test that all message categories exist."""

    def test_error_messages_exist(self):
        """Test error messages exist in all languages."""
        for lang in SUPPORTED_LANGUAGES:
            set_language(lang)
            assert t("error.model_not_found", model="x")
            assert t("error.connection_failed", host="x")

    def test_success_messages_exist(self):
        """Test success messages exist in all languages."""
        for lang in SUPPORTED_LANGUAGES:
            set_language(lang)
            assert t("success.model_pulled", model="x")

    def test_chat_messages_exist(self):
        """Test chat messages exist in all languages."""
        for lang in SUPPORTED_LANGUAGES:
            set_language(lang)
            assert t("chat.session_ended", turns=0, model="x")
            assert t("chat.history_cleared")

    def test_suggestion_messages_exist(self):
        """Test suggestion messages exist in all languages."""
        for lang in SUPPORTED_LANGUAGES:
            set_language(lang)
            assert t("suggestion.pull_model", model="x")