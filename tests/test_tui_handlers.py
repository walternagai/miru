"""Tests for miru/ui/tui image_screen and rename_screen handler logic."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from miru.ui.tui.image_screen import ImageScreen
from miru.ui.tui.rename_screen import RenameScreen


class TestImageScreen:
    def _make_screen(self):
        screen = ImageScreen()
        screen.dismiss = MagicMock()
        fake_app = MagicMock()
        return screen, fake_app

    def test_invalid_path_notifies(self) -> None:
        screen, fake_app = self._make_screen()
        with patch.object(ImageScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen.query_one = MagicMock(return_value=MagicMock(value="/nope/missing.png"))
            screen._confirm_add()
        assert fake_app.notify.called

    def test_valid_image_dismisses(self, tmp_path) -> None:
        from PIL import Image

        img = tmp_path / "foto.png"
        Image.new("RGB", (10, 10), color="red").save(img)

        screen, fake_app = self._make_screen()
        with patch.object(ImageScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen.query_one = MagicMock(return_value=MagicMock(value=str(img)))
            screen._confirm_add()
        screen.dismiss.assert_called_once_with(str(img))

    def test_empty_input_does_not_dismiss(self) -> None:
        screen, fake_app = self._make_screen()
        with patch.object(ImageScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen.query_one = MagicMock(return_value=MagicMock(value=""))
            screen._confirm_add()
        screen.dismiss.assert_not_called()


class TestRenameScreen:
    def _make_screen(self):
        screen = RenameScreen(session_name="old")
        screen.dismiss = MagicMock()
        fake_app = MagicMock()
        return screen, fake_app

    def test_invalid_name_notifies(self) -> None:
        screen, fake_app = self._make_screen()
        with patch.object(RenameScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen._confirm_rename("a/b")
        assert fake_app.notify.called
        screen.dismiss.assert_not_called()

    def test_same_name_dismisses_none(self) -> None:
        screen, fake_app = self._make_screen()
        with patch.object(RenameScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen._confirm_rename("old")
        screen.dismiss.assert_called_once_with(None)

    def test_valid_rename_dismisses(self, tmp_path, monkeypatch) -> None:
        import miru.ui.tui.rename_screen as rs_mod

        monkeypatch.setattr(rs_mod, "get_session_path", lambda name: tmp_path / f"{name}.json")
        screen, fake_app = self._make_screen()
        with patch.object(RenameScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen._confirm_rename("novo")
        screen.dismiss.assert_called_once_with("novo")

    def test_conflict_notifies(self, tmp_path, monkeypatch) -> None:
        import miru.ui.tui.rename_screen as rs_mod

        (tmp_path / "existente.json").write_text("{}")
        monkeypatch.setattr(rs_mod, "get_session_path", lambda name: tmp_path / f"{name}.json")
        screen, fake_app = self._make_screen()
        with patch.object(RenameScreen, "app", new_callable=PropertyMock, return_value=fake_app):
            screen._confirm_rename("existente")
        assert fake_app.notify.called
        screen.dismiss.assert_not_called()


class TestExportScreenHandlers:
    def test_radio_change_updates_path(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        path_input = MagicMock()
        path_input.value = "nome"
        screen.query_one = MagicMock(return_value=path_input)
        event = MagicMock()
        event.pressed.id = "fmt_txt"
        screen.on_radio_set_changed(event)
        assert path_input.value == "nome.txt"

    def test_radio_clipboard_clears_path(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        path_input = MagicMock()
        path_input.value = "nome.md"
        screen.query_one = MagicMock(return_value=path_input)
        event = MagicMock()
        event.pressed.id = "fmt_clip"
        screen.on_radio_set_changed(event)
        assert path_input.value == ""

    def test_radio_change_exception_logged(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        screen.query_one = MagicMock(side_effect=RuntimeError("boom"))
        event = MagicMock()
        event.pressed.id = "fmt_md"
        # não deve levantar
        screen.on_radio_set_changed(event)

    def test_get_format_mapping(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        pressed = MagicMock()
        pressed.id = "fmt_json"
        radio_set = MagicMock()
        radio_set.pressed_button = pressed
        screen.query_one = MagicMock(return_value=radio_set)
        assert screen._get_format() == "json"

    def test_get_format_fallback(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        screen.query_one = MagicMock(side_effect=RuntimeError("boom"))
        assert screen._get_format() == "markdown"

    def test_button_export_dismisses_with_format(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        screen.dismiss = MagicMock()
        screen._get_format = MagicMock(return_value="json")
        path_input = MagicMock()
        path_input.value = "arquivo"
        screen.query_one = MagicMock(return_value=path_input)
        event = MagicMock()
        event.button.id = "export_btn"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(("json", "arquivo"))

    def test_button_cancel_dismisses_none(self) -> None:
        from miru.ui.tui.export_screen import ExportScreen

        screen = ExportScreen(session_name="conv")
        screen.dismiss = MagicMock()
        event = MagicMock()
        event.button.id = "cancel_btn"
        screen.on_button_pressed(event)
        screen.dismiss.assert_called_once_with(None)
