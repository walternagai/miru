"""Tests for miru/ui/tui/config_screen.py using Textual's run_test pilot."""

from unittest.mock import patch

import pytest

from miru.core.config import Config
from miru.ui.tui.app import TUIApp
from miru.ui.tui.config_screen import ConfigScreen


def _make_config(**overrides):
    defaults = dict(
        default_host="http://localhost:11434",
        default_model="gemma3:27b-cloud",
        default_timeout=30.0,
        default_temperature=0.7,
        default_top_p=0.9,
        default_max_tokens=2048,
        default_seed=None,
        language="pt_BR",
        history_enabled=True,
        verbose=False,
        enable_tools=False,
        enable_tavily=False,
        tool_mode="auto_safe",
        sandbox_dir=None,
        history_max_entries=1000,
        tavily_api_key=None,
        profiles={},
        current_profile=None,
    )
    defaults.update(overrides)
    return Config(**defaults)


@pytest.fixture
def app():
    return TUIApp(model="test-model", host="http://localhost:11434")


async def _open_config(app, pilot):
    """Push ConfigScreen and wait until it is the active screen."""
    app.push_screen(ConfigScreen())
    for _ in range(10):
        await pilot.pause()
        if isinstance(app.screen, ConfigScreen):
            return app.screen
    raise AssertionError("ConfigScreen did not become the active screen")


@pytest.mark.asyncio
async def test_config_screen_mounts(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()):
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            assert screen.query_one("#config_host") is not None
            assert screen.query_one("#config_model") is not None


@pytest.mark.asyncio
async def test_config_screen_prefilled_values(app) -> None:
    config = _make_config(
        default_host="http://server:11434",
        default_model="llama3",
        default_timeout=45.0,
        language="en_US",
    )
    with patch("miru.ui.tui.config_screen.reload_config", return_value=config):
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            assert screen.query_one("#config_host").value == "http://server:11434"
            assert screen.query_one("#config_model").value == "llama3"
            assert screen.query_one("#config_timeout").value == "45.0"
            assert screen.query_one("#config_language").value == "en_US"


@pytest.mark.asyncio
async def test_save_config_calls_save(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()), \
         patch("miru.ui.tui.config_screen.save_config") as mock_save:
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            screen.query_one("#config_host").value = "http://new-host:11434"
            screen.query_one("#config_model").value = "qwen2.5"
            from textual.widgets import Button

            screen.query_one("#save_btn", Button).press()
            await pilot.pause()
            assert mock_save.called
            saved = mock_save.call_args.args[0]
            assert saved.default_host == "http://new-host:11434"
            assert saved.default_model == "qwen2.5"


@pytest.mark.asyncio
async def test_validation_host_required(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()), \
         patch("miru.ui.tui.config_screen.save_config") as mock_save:
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            screen.query_one("#config_host").value = ""
            from textual.widgets import Button

            screen.query_one("#save_btn", Button).press()
            await pilot.pause()
            assert not mock_save.called


@pytest.mark.asyncio
async def test_validation_timeout_positive(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()), \
         patch("miru.ui.tui.config_screen.save_config") as mock_save:
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            screen.query_one("#config_timeout").value = "-5"
            from textual.widgets import Button

            screen.query_one("#save_btn", Button).press()
            await pilot.pause()
            assert not mock_save.called


@pytest.mark.asyncio
async def test_validation_temperature_range(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()), \
         patch("miru.ui.tui.config_screen.save_config") as mock_save:
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            screen.query_one("#config_temp").value = "2.5"
            from textual.widgets import Button

            screen.query_one("#save_btn", Button).press()
            await pilot.pause()
            assert not mock_save.called


@pytest.mark.asyncio
async def test_reset_to_defaults(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config(
        default_host="http://custom:11434",
        default_timeout=99.0,
    )):
        async with app.run_test() as pilot:
            screen = await _open_config(app, pilot)
            from textual.widgets import Button

            screen.query_one("#reset_btn", Button).press()
            await pilot.pause()
            assert screen.query_one("#config_host").value == "http://localhost:11434"
            assert screen.query_one("#config_timeout").value == "30"
            assert screen.query_one("#config_language").value == "pt_BR"


@pytest.mark.asyncio
async def test_cancel_dismisses(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()):
        async with app.run_test() as pilot:
            await _open_config(app, pilot)
            from textual.widgets import Button

            app.screen.query_one("#cancel_btn", Button).press()
            for _ in range(10):
                await pilot.pause()
                if not isinstance(app.screen, ConfigScreen):
                    break
            assert not isinstance(app.screen, ConfigScreen)


@pytest.mark.asyncio
async def test_escape_dismisses(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()):
        async with app.run_test() as pilot:
            await _open_config(app, pilot)
            await pilot.press("escape")
            for _ in range(10):
                await pilot.pause()
                if not isinstance(app.screen, ConfigScreen):
                    break
            assert not isinstance(app.screen, ConfigScreen)


@pytest.mark.asyncio
async def test_save_dismisses_after_success(app) -> None:
    with patch("miru.ui.tui.config_screen.reload_config", return_value=_make_config()), \
         patch("miru.ui.tui.config_screen.save_config"):
        async with app.run_test() as pilot:
            await _open_config(app, pilot)
            from textual.widgets import Button

            app.screen.query_one("#save_btn", Button).press()
            for _ in range(10):
                await pilot.pause()
                if not isinstance(app.screen, ConfigScreen):
                    break
            assert not isinstance(app.screen, ConfigScreen)
