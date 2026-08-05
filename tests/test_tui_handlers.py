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
