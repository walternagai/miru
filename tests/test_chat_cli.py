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
