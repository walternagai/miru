"""Tests for miru/ui/tui/image_screen.py using run_test pilot."""

from unittest.mock import patch

import pytest

from miru.ui.tui.app import TUIApp
from miru.ui.tui.image_screen import ImageScreen


@pytest.fixture
def app():
    return TUIApp(model="test-model", host="http://localhost:11434")


async def _open_image_screen(app, pilot, current_count=0):
    app.push_screen(ImageScreen(current_count=current_count))
    for _ in range(10):
        await pilot.pause()
        if isinstance(app.screen, ImageScreen):
            return app.screen
    raise AssertionError("ImageScreen did not become the active screen")


@pytest.mark.asyncio
async def test_image_screen_mounts(app) -> None:
    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot)
        assert screen.query_one("#image_input") is not None
        assert screen.query_one("#add_btn") is not None


@pytest.mark.asyncio
async def test_pending_count_shown(app) -> None:
    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot, current_count=2)
        label = screen.query_one("#pending_count")
        assert "Imagens pendentes: 2" in str(label.render())


@pytest.mark.asyncio
async def test_pending_count_hidden_when_zero(app) -> None:
    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot, current_count=0)
        with pytest.raises(Exception):
            screen.query_one("#pending_count")


@pytest.mark.asyncio
async def test_empty_input_notifies(app) -> None:
    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot)
        from textual.widgets import Button

        screen.query_one("#add_btn", Button).press()
        await pilot.pause()
        # screen should still be active (no dismiss on empty input)
        assert isinstance(app.screen, ImageScreen)


@pytest.mark.asyncio
async def test_valid_image_dismisses_with_path(app, tmp_path) -> None:
    from PIL import Image

    img = tmp_path / "foto.png"
    Image.new("RGB", (10, 10), color="blue").save(img)

    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot)
        screen.query_one("#image_input").value = str(img)
        from textual.widgets import Button

        screen.query_one("#add_btn", Button).press()
        for _ in range(10):
            await pilot.pause()
            if not isinstance(app.screen, ImageScreen):
                break
        assert not isinstance(app.screen, ImageScreen)


@pytest.mark.asyncio
async def test_invalid_path_stays_open(app) -> None:
    async with app.run_test() as pilot:
        screen = await _open_image_screen(app, pilot)
        screen.query_one("#image_input").value = "/nope/missing.png"
        from textual.widgets import Button

        screen.query_one("#add_btn", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, ImageScreen)


@pytest.mark.asyncio
async def test_cancel_dismisses(app) -> None:
    async with app.run_test() as pilot:
        await _open_image_screen(app, pilot)
        from textual.widgets import Button

        app.screen.query_one("#cancel_btn", Button).press()
        for _ in range(10):
            await pilot.pause()
            if not isinstance(app.screen, ImageScreen):
                break
        assert not isinstance(app.screen, ImageScreen)
