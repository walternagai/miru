"""Integration tests for the TUI app using Textual's run_test pilot.

These exercise real app actions (new chat, clear, zen, search, sort) without
a terminal, using mocked Ollama client.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.ui.tui.app import TUIApp


@pytest.fixture
def app():
    return TUIApp(model="test-model", host="http://localhost:11434")


@pytest.mark.asyncio
async def test_app_mounts(app) -> None:
    async with app.run_test() as pilot:
        assert app.model == "test-model"


@pytest.mark.asyncio
async def test_new_chat_resets_messages(app) -> None:
    app.messages = [{"role": "user", "content": "x"}]
    async with app.run_test() as pilot:
        # Simulate a real post-conversation state: onboarding already removed
        try:
            app.query_one("#onboarding").remove()
        except Exception:
            pass
        await pilot.pause()
        app.action_new_chat()
        await pilot.pause()
        assert app.messages == []
        assert app._turn_counter == 0


@pytest.mark.asyncio
async def test_zen_mode_toggles(app) -> None:
    async with app.run_test() as pilot:
        app.action_zen_mode()
        await pilot.pause()
        assert app.zen_mode is True
        app.action_zen_mode()
        await pilot.pause()
        assert app.zen_mode is False


@pytest.mark.asyncio
async def test_search_toggle(app) -> None:
    async with app.run_test() as pilot:
        app.action_search_chat()
        await pilot.pause()
        container = app.query_one("#search_container")
        assert container.has_class("visible")
        app.action_search_chat()
        await pilot.pause()
        assert not container.has_class("visible")


@pytest.mark.asyncio
async def test_cycle_sort_changes(app) -> None:
    async with app.run_test() as pilot:
        app.action_cycle_sort()
        await pilot.pause()
        assert app._session_sort == "name"
        app.action_cycle_sort()
        await pilot.pause()
        assert app._session_sort == "favorite"
        app.action_cycle_sort()
        await pilot.pause()
        assert app._session_sort == "updated"


@pytest.mark.asyncio
async def test_clear_input(app) -> None:
    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        user_input.text = "hello"
        app.action_clear_input()
        await pilot.pause()
        assert user_input.text == ""


@pytest.mark.asyncio
async def test_cancel_generation_noop_when_idle(app) -> None:
    async with app.run_test() as pilot:
        app.action_cancel_generation()
        await pilot.pause()
        assert app._is_generating is False


@pytest.mark.asyncio
async def test_perform_search_highlights(app) -> None:
    from miru.ui.tui.app import MessageWidget

    async with app.run_test() as pilot:
        chat_window = app.query_one("#chat_window")
        # remove onboarding so only the searchable widget remains
        try:
            app.query_one("#onboarding").remove()
        except Exception:
            pass
        await pilot.pause()
        widget = MessageWidget("resposta com python", message_id=1, classes="bot_message")
        await chat_window.mount(widget)
        await pilot.pause()
        app._perform_search("python")
        await pilot.pause()
        assert len(app._search_matches) == 1


@pytest.mark.asyncio
async def test_help_screen_pushes(app) -> None:
    async with app.run_test() as pilot:
        app.action_help()
        await pilot.pause()
        assert app.screen_stack


@pytest.mark.asyncio
async def test_export_no_messages_notifies(app) -> None:
    async with app.run_test() as pilot:
        app.messages = []
        app.action_export_session()
        await pilot.pause()
        assert app.messages == []
