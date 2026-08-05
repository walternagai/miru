"""Tests for miru/ui/tui pure logic — helpers, validation, screens without event loop."""

from unittest.mock import MagicMock

import pytest

from miru.ui.tui.app import (
    SPINNER_FRAMES,
    _extract_code_blocks,
    _format_updated,
    _make_session_slug,
    _session_id,
)
from miru.ui.tui.export_screen import ExportScreen
from miru.ui.tui.help_screen import HelpScreen
from miru.ui.tui.rename_screen import validate_session_name


class TestTUIHelpers:
    def test_session_id_normalizes(self) -> None:
        assert _session_id("Minha Sessão!") == "session_Minha_Sessao_"

    def test_extract_code_blocks(self) -> None:
        text = "antes ```python\nprint(1)\n``` depois ```txt\na\nb\n```"
        blocks = _extract_code_blocks(text)
        assert "print(1)" in blocks
        assert "a\nb" in blocks

    def test_extract_code_blocks_none(self) -> None:
        assert _extract_code_blocks("sem blocos") == ""

    def test_make_session_slug(self) -> None:
        assert _make_session_slug("Olá Mundo teste") == "ola_mundo_teste"

    def test_make_session_slug_empty(self) -> None:
        assert _make_session_slug("!!!") == "chat"

    def test_format_updated(self) -> None:
        assert _format_updated("2026-04-01T12:00:00") == "01/04 12:00"

    def test_format_updated_empty(self) -> None:
        assert _format_updated("") == ""

    def test_format_updated_invalid(self) -> None:
        assert _format_updated("lixo") == "lixo"

    def test_spinner_frames(self) -> None:
        assert len(SPINNER_FRAMES) == 10


class TestValidateSessionName:
    def test_valid(self) -> None:
        ok, msg = validate_session_name("minha sessão")
        assert ok is True
        assert msg == ""

    def test_empty(self) -> None:
        ok, msg = validate_session_name("")
        assert ok is False
        assert "vazio" in msg

    def test_too_long(self) -> None:
        ok, _ = validate_session_name("x" * 101)
        assert ok is False

    def test_invalid_chars(self) -> None:
        ok, msg = validate_session_name("a/b")
        assert ok is False
        assert "inválidos" in msg

    def test_reserved_name(self) -> None:
        ok, msg = validate_session_name("CON")
        assert ok is False
        assert "reservado" in msg


class TestScreensCompose:
    # NOTE: compose() and event handlers of Textual screens require the
    # Textual event loop / compose stack (internals initialized only at
    # App.run()). Testing them without a driver is not viable — documented
    # as PENDING in the kata task. Pure logic (helpers, validation, format
    # mapping) is covered above.

    def test_export_format_ext_map(self) -> None:
        """The radio->extension mapping is pure logic worth covering."""
        from miru.ui.tui.export_screen import Input

        screen = ExportScreen(session_name="conv")
        path_input = MagicMock(spec=Input)
        path_input.value = "nome"
        screen.query_one = MagicMock(return_value=path_input)
        event = MagicMock()
        event.pressed.id = "fmt_json"
        screen.on_radio_set_changed(event)
        assert path_input.value == "nome.json"
