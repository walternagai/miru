"""Tests for miru/commands/chat.py CLI — validation and error paths."""

from unittest.mock import AsyncMock, patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestChatCli:
    def test_system_and_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("sys", encoding="utf-8")
        result = runner.invoke(
            app, ["chat", "gemma3", "--system", "x", "--system-file", str(f)]
        )
        assert result.exit_code == 1

    def test_missing_system_file(self) -> None:
        result = runner.invoke(
            app, ["chat", "gemma3", "--system-file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_success(self) -> None:
        with patch("miru.commands.chat._chat_async", new_callable=AsyncMock) as mock_chat, \
             patch("miru.commands.chat.set_language"):
            result = runner.invoke(app, ["chat", "gemma3", "--quiet"])
            assert result.exit_code == 0
            assert mock_chat.called


class TestChatCliWrapper:
    def test_system_and_file_conflict(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("sys", encoding="utf-8")
        result = runner.invoke(
            app, ["chat", "gemma3", "--system", "x", "--system-file", str(f)]
        )
        assert result.exit_code == 1

    def test_missing_system_file(self) -> None:
        result = runner.invoke(
            app, ["chat", "gemma3", "--system-file", "nope.txt"]
        )
        assert result.exit_code == 1

    def test_system_from_file(self, tmp_path) -> None:
        f = tmp_path / "s.txt"
        f.write_text("seja gentil", encoding="utf-8")
        with patch("miru.commands.chat._chat_async", new_callable=AsyncMock) as mock_chat, \
             patch("miru.commands.chat.set_language"):
            result = runner.invoke(
                app, ["chat", "gemma3", "--system-file", str(f), "--quiet"]
            )
            assert result.exit_code == 0
            assert mock_chat.called
            # system_prompt lido do arquivo
            call_kwargs = mock_chat.call_args.kwargs
            assert call_kwargs["system_prompt"] == "seja gentil"

    def test_system_inline(self) -> None:
        with patch("miru.commands.chat._chat_async", new_callable=AsyncMock) as mock_chat, \
             patch("miru.commands.chat.set_language"):
            result = runner.invoke(
                app, ["chat", "gemma3", "--system", "seja conciso", "--quiet"]
            )
            assert result.exit_code == 0
            assert mock_chat.call_args.kwargs["system_prompt"] == "seja conciso"

    def test_tools_resolved_from_cli(self) -> None:
        with patch("miru.commands.chat._chat_async", new_callable=AsyncMock) as mock_chat, \
             patch("miru.commands.chat.set_language"), \
             patch("miru.core.config.resolve_enable_tools", return_value=False):
            result = runner.invoke(
                app, ["chat", "gemma3", "--enable-tools", "--quiet"]
            )
            assert result.exit_code == 0
            assert mock_chat.call_args.kwargs["enable_tools"] is True

    def test_tools_from_config(self) -> None:
        with patch("miru.commands.chat._chat_async", new_callable=AsyncMock) as mock_chat, \
             patch("miru.commands.chat.set_language"), \
             patch("miru.core.config.resolve_enable_tools", return_value=True):
            result = runner.invoke(app, ["chat", "gemma3", "--quiet"])
            assert result.exit_code == 0
            assert mock_chat.call_args.kwargs["enable_tools"] is True
