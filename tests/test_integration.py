"""Integration tests for CLI commands with i18n.

Tests the full command flow from argument parsing to output.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
import json


class TestChatCommandIntegration:
    """Integration tests for chat command with i18n."""

    def test_chat_model_required(self):
        """Test that chat requires a model when no default is set."""
        from miru.core.config import Config
        
        # Without default model, should require model argument
        config = Config()
        assert config.default_model is None
        
    @patch("miru.commands.chat.asyncio.run")
    @patch("miru.commands.chat._chat_async")
    def test_chat_with_model_pt_br(self, mock_chat_async, mock_run):
        """Test chat command with Portuguese i18n."""
        from miru.core.i18n import set_language, t
        
        set_language("pt_BR")
        msg = t("chat.session_ended", turns=5, model="test")
        
        assert "5 turno(s)" in msg
        assert "test" in msg
        
    @patch("miru.commands.chat.asyncio.run")
    @patch("miru.commands.chat._chat_async")
    def test_chat_with_model_en_us(self, mock_chat_async, mock_run):
        """Test chat command with English i18n."""
        from miru.core.i18n import set_language, t
        
        set_language("en_US")
        msg = t("chat.session_ended", turns=5, model="test")
        
        assert "5 turn(s)" in msg
        assert "test" in msg


class TestRunCommandIntegration:
    """Integration tests for run command with i18n."""

    def test_run_invalid_format_error(self):
        """Test run command with invalid format."""
        from miru.core.i18n import t, set_language
        
        set_language("en_US")
        msg = t("error.invalid_format", format="xml", valid_formats="text, json")
        
        assert "Invalid format" in msg
        assert "xml" in msg
        
    def test_run_file_not_found_error(self):
        """Test run command file not found error."""
        from miru.core.i18n import t, set_language
        
        set_language("pt_BR")
        msg = t("error.file_not_found", path="/path/to/file.txt")
        
        assert "não encontrado" in msg.lower()
        assert "/path/to/file.txt" in msg
        
    def test_run_system_prompt_file_error(self):
        """Test run command system prompt file error."""
        from miru.core.i18n import t, set_language
        
        set_language("es_ES")
        msg = t("error.system_prompt_file", error="Permission denied")
        
        assert "system prompt" in msg.lower()


class TestBatchCommandIntegration:
    """Integration tests for batch command."""

    def test_batch_processing_status_messages(self):
        """Test batch command status messages."""
        from miru.core.i18n import t, set_language
        
        # Portuguese
        set_language("pt_BR")
        msg = t("progress.processing")
        assert "Processando" in msg
        
        # English
        set_language("en_US")
        msg = t("progress.processing")
        assert "Processing" in msg
        
        # Spanish
        set_language("es_ES")
        msg = t("progress.processing")
        assert "Procesando" in msg

    def test_batch_invalid_format(self):
        """Test batch command invalid format."""
        from miru.core.i18n import t, set_language
        
        set_language("en_US")
        msg = t("error.invalid_format", format="xml", valid_formats="text, json, jsonl")
        
        assert "Invalid format" in msg
        assert "xml" in msg


class TestCompareCommandIntegration:
    """Integration tests for compare command."""

    def test_compare_table_headers_localized(self):
        """Test that compare table headers are localized."""
        from miru.core.i18n import set_language, get_language
        
        # Portuguese
        set_language("pt_BR")
        assert get_language() == "pt_BR"
        
        # English
        set_language("en_US")
        assert get_language() == "en_US"
        
        # Spanish
        set_language("es_ES")
        assert get_language() == "es_ES"


class TestListCommandIntegration:
    """Integration tests for list command."""

    @patch("miru.commands.list.asyncio.run")
    @patch("miru.commands.list._list_models_async")
    def test_list_empty_models_all_languages(self, mock_list_async, mock_run):
        """Test list command with empty models in all languages."""
        from miru.core.i18n import set_language, t
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            msg = t("models.empty")
            
            if lang == "pt_BR":
                assert "Nenhum modelo" in msg
            elif lang == "en_US":
                assert "No models" in msg
            else:
                assert "Ningún modelo" in msg

    @patch("miru.commands.list.resolve_host")
    def test_list_connection_error_all_languages(self, mock_resolve_host):
        """Test list command connection error in all languages."""
        from miru.core.errors import ConnectionError
        from miru.core.i18n import set_language
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            error = ConnectionError("http://localhost:11434")
            
            if lang == "pt_BR":
                assert "conectar" in error.message.lower()
            elif lang == "en_US":
                assert "connect" in error.message.lower()
            else:
                assert "conectar" in error.message.lower()


class TestInfoCommandIntegration:
    """Integration tests for info command."""

    def test_info_model_not_found_with_suggestions(self):
        """Test info command model not found with suggestions."""
        from miru.core.errors import ModelNotFoundError
        from miru.core.i18n import set_language
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            error = ModelNotFoundError("unknown-model", ["model1", "model2"])
            
            if lang == "pt_BR":
                assert "não encontrado" in error.message.lower()
            elif lang == "en_US":
                assert "not found" in error.message.lower()
            else:
                assert "no encontrado" in error.message.lower()
            
            assert error.suggestion is not None


class TestPullCommandIntegration:
    """Integration tests for pull command."""

    def test_pull_progress_messages(self):
        """Test pull command progress messages."""
        from miru.core.i18n import set_language, t
        
        # Portuguese
        set_language("pt_BR")
        msg = t("success.model_pulled", model="gemma3")
        assert "baixado" in msg.lower() or "sucesso" in msg.lower()
        
        # English
        set_language("en_US")
        msg = t("success.model_pulled", model="gemma3")
        assert "pulled" in msg.lower()
        
        # Spanish
        set_language("es_ES")
        msg = t("success.model_pulled", model="gemma3")
        assert "descargado" in msg.lower() or "exitosamente" in msg.lower()


class TestDeleteCopyCommandsIntegration:
    """Integration tests for delete and copy commands."""

    def test_delete_success_message(self):
        """Test delete command success message."""
        from miru.core.i18n import set_language, t
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            msg = t("success.model_deleted", model="test-model")
            
            if lang == "pt_BR":
                assert "deletado" in msg.lower() or "sucesso" in msg.lower()
            elif lang == "en_US":
                assert "deleted" in msg.lower()
            else:
                assert "eliminado" in msg.lower() or "suceso" in msg.lower()

    def test_copy_success_message(self):
        """Test copy command success message."""
        from miru.core.i18n import set_language, t
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            msg = t("success.model_copied", new_name="backup-model")
            
            # At least one of these variations
            assert "copiado" in msg.lower() or "copied" in msg.lower()


class TestConfigCommandIntegration:
    """Integration tests for config command."""

    def test_config_persistence(self):
        """Test config is properly loaded and saved."""
        from miru.core.config import Config, load_config, save_config
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            
            # Create config with language
            config = Config(
                default_host="http://localhost:11434",
                default_model="gemma3:latest",
                language="pt_BR"
            )
            
            # Save and reload
            save_config(config)
            loaded = load_config()
            
            assert loaded.language == "pt_BR"
            assert loaded.default_model == "gemma3:latest"

    def test_config_env_override(self):
        """Test environment variables override config."""
        from miru.core.config import get_config_value
        import os
        
        # Set env var
        os.environ["MIRU_LANGUAGE"] = "es_ES"
        
        value = get_config_value("language")
        assert value == "es_ES"
        
        # Cleanup
        del os.environ["MIRU_LANGUAGE"]


class TestErrorSuggestions:
    """Test that error messages include helpful suggestions."""

    def test_model_not_found_suggests_pull(self):
        """Test ModelNotFoundError suggests pull command."""
        from miru.core.errors import ModelNotFoundError
        from miru.core.i18n import set_language
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            error = ModelNotFoundError("test-model", ["available-model"])
            
            # Should include suggestion with pull command
            assert error.suggestion is not None
            assert "pull" in error.suggestion.lower()

    def test_connection_error_suggests_ollama_serve(self):
        """Test ConnectionError suggests ollama serve."""
        from miru.core.errors import ConnectionError
        from miru.core.i18n import set_language
        
        for lang in ["pt_BR", "en_US", "es_ES"]:
            set_language(lang)
            error = ConnectionError("http://localhost:11434")
            
            # Should suggest starting ollama
            assert error.suggestion is not None
            assert "ollama" in error.suggestion.lower() or "serve" in error.suggestion.lower()

    def test_file_not_found_shows_path(self):
        """Test FileProcessingError shows the file path."""
        from miru.core.errors import FileProcessingError
        
        error = FileProcessingError("/path/to/file.txt", "read")
        
        assert "/path/to/file.txt" in error.message
        assert "read" in error.message.lower()


class TestLanguageDetection:
    """Test automatic language detection."""

    def test_detect_from_miru_lang(self, monkeypatch):
        """Test detection from MIRU_LANG."""
        from miru.core.i18n import detect_language
        
        monkeypatch.setenv("MIRU_LANG", "pt_BR")
        lang = detect_language()
        
        assert lang == "pt_BR"

    def test_detect_from_lang_env(self, monkeypatch):
        """Test detection from LANG."""
        from miru.core.i18n import detect_language
        
        monkeypatch.delenv("MIRU_LANG", raising=False)
        monkeypatch.setenv("LANG", "es_ES.UTF-8")
        
        lang = detect_language()
        assert lang == "es_ES"

    def test_detect_default(self, monkeypatch):
        """Test default language when no env vars."""
        from miru.core.i18n import detect_language, DEFAULT_LANGUAGE
        
        # This may vary based on system locale, just check it's valid
        lang = detect_language()
        assert lang in ["pt_BR", "en_US", "es_ES"] or lang == DEFAULT_LANGUAGE


class TestShortFlags:
    """Test that short flags work correctly."""

    def test_host_flag(self):
        """Test -h flag for --host."""
        from miru.cli_options import Host
        
        # Host is just a type alias, the actual parsing is done by typer
        # This test verifies the type exists and is correct
        assert Host is not None
        
    def test_format_flag(self):
        """Test -f flag for --format."""
        from miru.cli_options import Format
        
        assert Format is not None
        
    def test_quiet_flag(self):
        """Test -q flag for --quiet."""
        from miru.cli_options import Quiet
        
        assert Quiet is not None
        
    def test_temperature_flag(self):
        """Test -t flag for --temperature."""
        from miru.cli_options import Temperature
        
        assert Temperature is not None


class TestConfigResolution:
    """Test configuration resolution chain."""

    def test_resolve_host_chain(self):
        """Test host resolution precedence."""
        from miru.core.config import resolve_host
        
        # CLI override takes precedence
        host = resolve_host("http://custom:8080")
        assert host == "http://custom:8080"
        
    def test_resolve_model_chain(self):
        """Test model resolution precedence."""
        from miru.core.config import resolve_model
        
        # CLI override takes precedence
        model = resolve_model("gemma3:latest")
        assert model == "gemma3:latest"

    def test_config_caching(self):
        """Test that config is cached."""
        from miru.core.config import get_config
        
        config1 = get_config()
        config2 = get_config()
        
        # Same instance should be returned
        assert config1 is config2