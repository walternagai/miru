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


@pytest.mark.asyncio
async def test_export_session_with_messages(app, tmp_path, monkeypatch) -> None:
    """Export de sessão com mensagens → arquivo criado no path."""
    import miru.ui.tui.app as app_mod
    from miru.session import export_session

    app.messages = [{"role": "user", "content": "olá"}, {"role": "assistant", "content": "oi"}]
    app.current_session_name = None  # unsaved → _export_unsaved
    out = tmp_path / "export.md"
    async with app.run_test() as pilot:
        with patch.object(app_mod, "export_session") as mock_export:
            app._on_export_complete(("markdown", str(out)))
            await pilot.pause()
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "olá" in text


@pytest.mark.asyncio
async def test_export_clipboard(app) -> None:
    app.messages = [{"role": "user", "content": "pergunta"}, {"role": "assistant", "content": "resposta"}]
    async with app.run_test() as pilot:
        app._on_export_complete(("clipboard", ""))
        await pilot.pause()


@pytest.mark.asyncio
async def test_export_no_messages_notifies(app) -> None:
    async with app.run_test() as pilot:
        app.action_export_session()
        await pilot.pause()
        assert app.messages == []


@pytest.mark.asyncio
async def test_save_session_creates_file(app, tmp_path, monkeypatch) -> None:
    import miru.ui.tui.app as app_mod
    from miru.session import save_session as real_save

    app.messages = [{"role": "user", "content": "x"}]
    app.current_session_name = "conv-teste"
    async with app.run_test() as pilot:
        with patch.object(app_mod, "save_session") as mock_save:
            app.action_save_session()
            await pilot.pause()
            mock_save.assert_called_once_with("conv-teste", app.model, app.messages)


@pytest.mark.asyncio
async def test_update_chat_header_with_stats(app) -> None:
    app._session_tokens = 100
    app._session_tps = 5.0
    async with app.run_test() as pilot:
        app._update_chat_header()
        await pilot.pause()
        header = app.query_one("#chat_header")
        assert "100" in str(header.render())


@pytest.mark.asyncio
async def test_filter_sessions(app) -> None:
    async with app.run_test() as pilot:
        app.refresh_sessions()
        await pilot.pause()
        app.filter_sessions("zzz-nonexistent")
        await pilot.pause()


@pytest.mark.asyncio
async def test_clear_chat_confirm(app) -> None:
    app.messages = [{"role": "user", "content": "x"}]
    async with app.run_test() as pilot:
        app.action_clear_chat()
        await pilot.pause()
        # ConfirmScreen pushed
        assert app.screen_stack


@pytest.mark.asyncio
async def test_reload_sessions(app) -> None:
    async with app.run_test() as pilot:
        app.action_reload_sessions()
        await pilot.pause()


@pytest.mark.asyncio
async def test_confirm_clear_removes_messages(app) -> None:
    app.messages = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}]
    app._turn_counter = 3
    async with app.run_test() as pilot:
        app._on_confirm_clear(True)
        await pilot.pause()
        assert app.messages == []
        assert app._turn_counter == 0


@pytest.mark.asyncio
async def test_confirm_clear_cancelled_keeps(app) -> None:
    app.messages = [{"role": "user", "content": "x"}]
    async with app.run_test() as pilot:
        app._on_confirm_clear(False)
        await pilot.pause()
        assert len(app.messages) == 1


@pytest.mark.asyncio
async def test_confirm_delete_removes(app, tmp_path, monkeypatch) -> None:
    import miru.ui.tui.app as app_mod

    app.messages = [{"role": "user", "content": "x"}]
    app.current_session_name = "conv"
    async with app.run_test() as pilot:
        with patch.object(app_mod, "delete_session", return_value=True) as mock_del:
            app._on_confirm_delete(True)
            await pilot.pause()
            mock_del.assert_called_once_with("conv")
            assert app.current_session_name is None


@pytest.mark.asyncio
async def test_rename_complete(app) -> None:
    app.current_session_name = "old"
    async with app.run_test() as pilot:
        with patch.object(app, "_rename_session_file", return_value=True) as mock_rename:
            app._on_rename_complete("new")
            await pilot.pause()
            mock_rename.assert_called_once_with("old", "new")
            assert app.current_session_name == "new"


@pytest.mark.asyncio
async def test_navigate_msg_up_down(app) -> None:
    from miru.ui.tui.app import MessageWidget

    async with app.run_test() as pilot:
        chat_window = app.query_one("#chat_window")
        try:
            app.query_one("#onboarding").remove()
        except Exception:
            pass
        await pilot.pause()
        for i in range(2):
            w = MessageWidget(f"msg {i}", message_id=i, classes="bot_message")
            await chat_window.mount(w)
        await pilot.pause()
        app.action_navigate_msg_up()
        await pilot.pause()
        app.action_navigate_msg_down()
        await pilot.pause()
        # não deve levantar


@pytest.mark.asyncio
async def test_history_navigation(app) -> None:
    app._input_history = ["msg1", "msg2"]
    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        app.action_history_up()
        await pilot.pause()
        app.action_history_down()
        await pilot.pause()
        assert user_input is not None


@pytest.mark.asyncio
async def test_toggle_favorite_no_session(app) -> None:
    app.current_session_name = None
    async with app.run_test() as pilot:
        app.action_toggle_favorite()
        await pilot.pause()


@pytest.mark.asyncio
async def test_run_llm_response_success(app) -> None:
    """Fluxo completo: run_llm_response com OllamaClient mockado."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)  # deixa o Textual montar o bot_msg
        yield {"message": {"content": "resposta"}, "done": True,
               "eval_count": 5, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.get_config", return_value=MagicMock()):
            await app.run_llm_response("pergunta", user_msg_dict={"role": "user", "content": "pergunta"})
            await pilot.pause()
    assert app._is_generating is False
    assert any(m.get("role") == "assistant" for m in app.messages)


@pytest.mark.asyncio
async def test_run_llm_response_connection_error(app) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch
    from miru.ollama.client import OllamaConnectionError

    client = MagicMock()
    client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("down"))
    client.__aexit__ = AsyncMock(return_value=None)

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.MessageWidget.query_one", return_value=MagicMock()) as mock_q:
            await app.run_llm_response("pergunta")
            await pilot.pause()
    assert app._is_generating is False
    assert mock_q.called  # fluxo de erro atualizou o widget


@pytest.mark.asyncio
async def test_run_llm_response_model_not_found(app) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch
    from miru.ollama.client import OllamaModelNotFound

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    async def chat_gen():
        await asyncio.sleep(0)
        raise OllamaModelNotFound("x")
        yield  # pragma: no cover

    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.MessageWidget.query_one", return_value=MagicMock()) as mock_q:
            await app.run_llm_response("pergunta")
            await pilot.pause()
    assert app._is_generating is False
    assert mock_q.called
