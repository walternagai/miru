"""Tests for miru/ui/tui/preset_screen.py and rename_screen.py pure handlers."""

from unittest.mock import MagicMock

from miru.ui.tui.preset_screen import PRESETS, PresetScreen, _preset_id


class TestPresetId:
    def test_normalizes(self) -> None:
        assert _preset_id("Programador") == "preset_programador"

    def test_returns_lowercase(self) -> None:
        assert _preset_id("Preciso").islower()


class TestPresetScreenHandlers:
    def _make_screen(self):
        screen = PresetScreen()
        screen.dismiss = MagicMock()
        return screen

    def test_key_digit_dismisses_preset(self) -> None:
        from textual.events import Key

        screen = self._make_screen()
        event = MagicMock(spec=Key)
        event.character = "1"
        event.key = ""
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(list(PRESETS.keys())[0])

    def test_key_escape_dismisses_none(self) -> None:
        from textual.events import Key

        screen = self._make_screen()
        event = MagicMock(spec=Key)
        event.character = ""
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)

    def test_key_out_of_range_ignored(self) -> None:
        from textual.events import Key

        screen = self._make_screen()
        event = MagicMock(spec=Key)
        event.character = "9"
        event.key = ""
        screen.on_key(event)
        screen.dismiss.assert_not_called()

    def test_button_cancel(self) -> None:
        from textual.widgets import Button

        screen = self._make_screen()
        event = MagicMock()
        event.button = MagicMock(spec=Button)
        event.button.id = "cancel_button"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(None)

    def test_button_preset(self) -> None:
        from textual.widgets import Button

        screen = self._make_screen()
        event = MagicMock()
        event.button = MagicMock(spec=Button)
        target = list(PRESETS.keys())[0]
        event.button.id = _preset_id(target)
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(target)

    def test_short_desc(self) -> None:
        screen = PresetScreen()
        assert screen._get_short_desc("Preciso") != ""
        assert screen._get_short_desc("Inexistente") == ""
