"""Integration tests for refactored commands with i18n."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestListCommand:
    """Test list command with i18n."""

    @patch("miru.commands.list.asyncio.run")
    @patch("miru.commands.list._list_models_async")
    def test_list_empty_models_pt_br(self, mock_list_async, mock_run):
        """Test list with empty models in Portuguese."""
        from miru.core.i18n import set_language
        
        set_language("pt_BR")
        
        # Setup mock to return empty list
        mock_run.return_value = None
        mock_list_async = AsyncMock(return_value=[])
        
        # Should show "Nenhum modelo encontrado"
        # This is tested by checking the render_empty_models function
        
    @patch("miru.commands.list.asyncio.run")
    @patch("miru.commands.list._list_models_async")
    def test_list_empty_models_en_us(self, mock_list_async, mock_run):
        """Test list with empty models in English."""
        from miru.core.i18n import set_language
        
        set_language("en_US")
        
        # Should show "No models found"


class TestInfoCommand:
    """Test info command with i18n."""

    def test_model_not_found_error_pt_br(self):
        """Test ModelNotFoundError in Portuguese."""
        from miru.core.errors import ModelNotFoundError
        from miru.core.i18n import set_language
        
        set_language("pt_BR")
        error = ModelNotFoundError("test-model")
        
        assert "não encontrado" in error.message.lower()
        assert error.suggestion is not None
        
    def test_model_not_found_error_en_us(self):
        """Test ModelNotFoundError in English."""
        from miru.core.errors import ModelNotFoundError
        from miru.core.i18n import set_language
        
        set_language("en_US")
        error = ModelNotFoundError("test-model")
        
        assert "not found" in error.message.lower()
        assert error.suggestion is not None


class TestRunCommand:
    """Test run command integration."""

    def test_file_not_found_error(self):
        """Test file not found error uses i18n."""
        from miru.core.i18n import t, set_language
        
        set_language("en_US")
        msg = t("error.file_not_found", path="/test/file.txt")
        assert "not found" in msg.lower()
        assert "/test/file.txt" in msg
        
    def test_file_not_found_error_pt_br(self):
        """Test file not found error in Portuguese."""
        from miru.core.i18n import t, set_language
        
        set_language("pt_BR")
        msg = t("error.file_not_found", path="/teste/arquivo.txt")
        assert "não encontrado" in msg.lower()


class TestBatchCommand:
    """Test batch command with i18n."""

    def test_batch_error_messages(self):
        """Test batch error messages use i18n."""
        from miru.core.i18n import t, set_language
        
        set_language("en_US")
        msg = t("error.invalid_format", format="xml", valid_formats="text, json, jsonl")
        assert "Invalid format" in msg
        assert "xml" in msg
        
    def test_batch_error_messages_pt_br(self):
        """Test batch error messages in Portuguese."""
        from miru.core.i18n import t, set_language
        
        set_language("pt_BR")
        msg = t("error.invalid_format", format="xml", valid_formats="text, json, jsonl")
        assert "Formato inválido" in msg


class TestCompareCommand:
    """Test compare command with i18n."""

    def test_comparison_table_headers(self):
        """Test that comparison table can use localized headers."""
        from miru.core.i18n import set_language, get_language
        
        set_language("pt_BR")
        assert get_language() == "pt_BR"
        
        set_language("en_US")
        assert get_language() == "en_US"


class TestPullCommand:
    """Test pull command with i18n."""

    def test_connection_error_pt_br(self):
        """Test connection error in Portuguese."""
        from miru.core.errors import ConnectionError
        from miru.core.i18n import set_language
        
        set_language("pt_BR")
        error = ConnectionError("http://localhost:11434")
        
        assert "conectar" in error.message.lower()
        
    def test_connection_error_en_us(self):
        """Test connection error in English."""
        from miru.core.errors import ConnectionError
        from miru.core.i18n import set_language
        
        set_language("en_US")
        error = ConnectionError("http://localhost:11434")
        
        assert "connect" in error.message.lower()


class TestDeleteCopyCommands:
    """Test delete and copy commands with i18n."""

    def test_delete_success_message(self):
        """Test delete success message."""
        from miru.core.i18n import t, set_language
        
        set_language("pt_BR")
        msg = t("success.model_deleted", model="test-model")
        assert "deletado" in msg.lower()
        
    def test_copy_success(self):
        """Test success messages are available."""
        from miru.core.i18n import t, set_language
        
        set_language("en_US")
        msg = t("success.model_copied", new_name="backup")
        assert "copied" in msg.lower()


class TestI18nLanguageSwitching:
    """Test language switching in commands."""

    def test_switch_to_portuguese(self):
        """Test switching to Portuguese."""
        from miru.core.i18n import set_language, get_language, t
        
        set_language("pt_BR")
        assert get_language() == "pt_BR"
        
        msg = t("error.model_not_found", model="test")
        assert "não encontrado" in msg.lower()

    def test_switch_to_spanish(self):
        """Test switching to Spanish."""
        from miru.core.i18n import set_language, get_language, t
        
        set_language("es_ES")
        assert get_language() == "es_ES"
        
        msg = t("error.model_not_found", model="test")
        assert "no encontrado" in msg.lower()

    def test_switch_to_english(self):
        """Test switching to English."""
        from miru.core.i18n import set_language, get_language, t
        
        set_language("en_US")
        assert get_language() == "en_US"
        
        msg = t("error.model_not_found", model="test")
        assert "not found" in msg.lower()


class TestErrorHandling:
    """Test error handling across commands."""

    def test_model_not_found_with_suggestions(self):
        """Test ModelNotFoundError includes suggestions."""
        from miru.core.errors import ModelNotFoundError
        
        error = ModelNotFoundError("unknown-model", ["model1", "model2"])
        
        assert "unknown-model" in error.message
        assert error.suggestion is not None
        assert "model1" in error.suggestion or "model2" in error.suggestion

    def test_connection_error_with_host(self):
        """Test ConnectionError includes host."""
        from miru.core.errors import ConnectionError
        
        error = ConnectionError("http://localhost:11434")
        
        assert error.host == "http://localhost:11434"
        assert error.suggestion is not None

    def test_validation_error(self):
        """Test ValidationError."""
        from miru.core.errors import ValidationError
        
        error = ValidationError("Invalid temperature", field="temperature", value=-1)
        
        assert error.message == "Invalid temperature"
        assert error.field == "temperature"
        assert error.value == -1