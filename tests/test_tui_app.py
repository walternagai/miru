"""Integration tests for the TUI app using Textual's run_test pilot.

These exercise real app actions (new chat, clear, zen, search, sort) without
a terminal, using mocked Ollama client.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.ui.tui.app import TUIApp, _session_id


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


@pytest.mark.asyncio
async def test_run_llm_response_with_images(app) -> None:
    """run_llm_response com imagens pendentes → encode_images chamado."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "resp"}, "done": True,
               "eval_count": 3, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = ["foto.png"]
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.input.image.encode_images", return_value=["b64"]) as mock_encode:
            await app.run_llm_response("pergunta", user_msg_dict={"role": "user", "content": "pergunta"})
            await pilot.pause()
    assert mock_encode.called
    assert app._is_generating is False


@pytest.mark.asyncio
async def test_run_llm_response_with_tools(app) -> None:
    """run_llm_response com tools habilitadas → execute_tool_loop."""
    from unittest.mock import AsyncMock, MagicMock, patch

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    app.enable_tools = True
    app.pending_images = []
    async with app.run_test() as pilot:
        async def fake_loop(*a, **k):
            await asyncio.sleep(0)  # deixa o Textual montar o bot_msg
            return "resposta da tool"

        fake_loop_mock = AsyncMock(side_effect=fake_loop)
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.tool_integration.execute_tool_loop", new=fake_loop_mock) as mock_loop:
            await app.run_llm_response("pergunta", user_msg_dict={"role": "user", "content": "pergunta"})
            await pilot.pause()
    assert mock_loop.called
    assert app._is_generating is False


@pytest.mark.asyncio
async def test_run_llm_response_skip_user_append(app) -> None:
    """skip_user_append=True → mensagem do usuário NÃO é re-adicionada."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "nova resp"}, "done": True,
               "eval_count": 1, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    app.messages = [{"role": "user", "content": "pergunta original"}]
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client):
            await app.run_llm_response("pergunta original", skip_user_append=True)
            await pilot.pause()
    assert app._is_generating is False
    user_msgs = [m for m in app.messages if m.get("role") == "user"]
    assert len(user_msgs) == 1  # não duplicou


@pytest.mark.asyncio
async def test_regenerate_last_message(app) -> None:
    """regenerate_last_message remove a última assistant e re-executa."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "regenerada"}, "done": True,
               "eval_count": 1, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    app.messages = [
        {"role": "user", "content": "pergunta"},
        {"role": "assistant", "content": "resposta antiga"},
    ]
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client):
            app.regenerate_last_message()
            await pilot.pause()
            await pilot.pause()
    assert app._is_generating is False
    assert app.messages[-1]["content"] == "regenerada"


@pytest.mark.asyncio
async def test_regenerate_blocked_while_generating(app) -> None:
    app._is_generating = True
    async with app.run_test() as pilot:
        app.regenerate_last_message()
        await pilot.pause()
        assert app._is_generating is True  # bloqueado


@pytest.mark.asyncio
async def test_cancel_generation_with_worker(app) -> None:
    from unittest.mock import MagicMock

    worker = MagicMock()
    app._is_generating = True
    app._current_worker = worker
    async with app.run_test() as pilot:
        app.action_cancel_generation()
        await pilot.pause()
        worker.cancel.assert_called_once()
        assert app._is_generating is False


@pytest.mark.asyncio
async def test_load_session_renders_messages(app, tmp_path, monkeypatch) -> None:
    """Carregar sessão → mensagens renderizadas como widgets."""
    import miru.ui.tui.app as app_mod

    session_data = {
        "name": "conv1",
        "model": "gemma3",
        "messages": [
            {"role": "user", "content": "pergunta", "_ts": "10:00"},
            {"role": "assistant", "content": "resposta"},
        ],
    }
    monkeypatch.setattr(app_mod, "load_session", lambda name: session_data)

    async with app.run_test() as pilot:
        app.refresh_sessions()
        await pilot.pause()
        # simula seleção de item da lista
        from unittest.mock import MagicMock

        event = MagicMock()
        event.item.id = _session_id("conv1")
        event.item.add_class = MagicMock()
        app._session_id_to_name = {_session_id("conv1"): "conv1"}
        app.on_list_view_selected(event)
        await pilot.pause()
        assert app.current_session_name == "conv1"
        assert len(app.messages) == 2


@pytest.mark.asyncio
async def test_toggle_favorite_with_session(app, tmp_path, monkeypatch) -> None:
    """Favoritar sessão com current_session_name definido."""
    import miru.ui.tui.app as app_mod

    app.current_session_name = "conv1"
    with patch.object(app_mod, "toggle_favorite", return_value=True) as mock_toggle, \
         patch.object(app_mod, "load_favorites", return_value=set()):
        async with app.run_test() as pilot:
            app.action_toggle_favorite()
            await pilot.pause()
            mock_toggle.assert_called_once_with("conv1")


@pytest.mark.asyncio
async def test_add_image_opens_screen(app) -> None:
    """action_add_image → push ImageScreen."""
    async with app.run_test() as pilot:
        app.action_add_image()
        await pilot.pause()
        assert app.screen_stack  # modal pushado


@pytest.mark.asyncio
async def test_update_pending_images_indicator(app) -> None:
    """Indicador de imagens pendentes."""
    async with app.run_test() as pilot:
        app.pending_images = ["foto.png"]
        app._update_pending_images_indicator()
        await pilot.pause()
        app.pending_images = []
        app._update_pending_images_indicator()
        await pilot.pause()


@pytest.mark.asyncio
async def test_open_config_screen(app) -> None:
    """action_open_config → push ConfigScreen (screen real)."""
    from miru.ui.tui.config_screen import ConfigScreen

    async with app.run_test() as pilot:
        app.action_open_config()
        await pilot.pause()
        assert app.screen_stack  # modal pushado


@pytest.mark.asyncio
async def test_rename_session_file_success(app, tmp_path, monkeypatch) -> None:
    """_rename_session_file: sucesso com favorito migrado."""
    import miru.ui.tui.app as app_mod

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    old = sessions_dir / "old.json"
    old.write_text('{"name": "old", "messages": []}', encoding="utf-8")

    monkeypatch.setattr(app_mod, "load_session", lambda n: {"name": n, "messages": []})
    monkeypatch.setattr(app_mod, "load_favorites", lambda: {"old"})
    monkeypatch.setattr(app_mod, "save_favorites", lambda f: None)
    monkeypatch.setattr(app_mod, "CONFIG_DIR", tmp_path)

    async with app.run_test() as pilot:
        ok = app._rename_session_file("old", "new")
        await pilot.pause()
    assert ok is True
    assert (sessions_dir / "new.json").exists()
    assert not (sessions_dir / "old.json").exists()


@pytest.mark.asyncio
async def test_rename_session_file_missing(app, monkeypatch) -> None:
    """_rename_session_file: sessão não existe → False."""
    import miru.ui.tui.app as app_mod

    monkeypatch.setattr(app_mod, "load_session", lambda n: None)
    async with app.run_test() as pilot:
        ok = app._rename_session_file("nope", "new")
        await pilot.pause()
    assert ok is False


@pytest.mark.asyncio
async def test_submit_message_empty_returns(app) -> None:
    """action_submit_message com input vazio → return sem efeito."""
    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        user_input.text = "   "
        app.action_submit_message()
        await pilot.pause()
        assert app.messages == []


@pytest.mark.asyncio
async def test_submit_message_while_generating(app) -> None:
    """action_submit_message bloqueado durante geração."""
    app._is_generating = True
    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        user_input.text = "olá"
        app.action_submit_message()
        await pilot.pause()
        assert app.messages == []  # bloqueado


@pytest.mark.asyncio
async def test_run_llm_response_streaming_progress(app) -> None:
    """Streaming com múltiplos chunks → progress no status e metrics montado."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "primeira parte"}, "done": False}
        await asyncio.sleep(0)
        yield {"message": {"content": "segunda parte"}, "done": True,
               "eval_count": 8, "eval_duration": 2_000_000_000,
               "total_duration": 2_500_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.save_session", new_callable=AsyncMock):
            await app.run_llm_response("pergunta", user_msg_dict={"role": "user", "content": "pergunta"})
            await pilot.pause()
    assert app._is_generating is False
    assert app._session_tokens == 8
    # mensagens salvas
    assert any(m.get("role") == "assistant" for m in app.messages)


@pytest.mark.asyncio
async def test_run_llm_response_save_error(app) -> None:
    """Erro ao salvar sessão → notify de erro."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "resp"}, "done": True,
               "eval_count": 1, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.save_session", new_callable=AsyncMock,
                   side_effect=RuntimeError("disco cheio")):
            await app.run_llm_response("pergunta")
            await pilot.pause()
    assert app._is_generating is False


@pytest.mark.asyncio
async def test_run_llm_response_tps_from_total(app) -> None:
    """eval_duration=0 mas total_duration>0 → tps calculado via total."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "resp"}, "done": True,
               "eval_count": 10, "eval_duration": 0,
               "total_duration": 2_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.save_session", new_callable=AsyncMock):
            await app.run_llm_response("pergunta", user_msg_dict={"role": "user", "content": "pergunta"})
            await pilot.pause()
    assert app._is_generating is False
    assert app._session_tokens == 10
    assert app._session_tps > 0  # calculado via total_duration


@pytest.mark.asyncio
async def test_run_llm_response_without_user_msg_dict(app) -> None:
    """user_msg_dict=None → mensagem criada de prompt (branch msg)."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        yield {"message": {"content": "resp"}, "done": True,
               "eval_count": 1, "eval_duration": 1_000_000_000,
               "total_duration": 1_000_000_000}

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.save_session", new_callable=AsyncMock):
            await app.run_llm_response("pergunta")  # sem user_msg_dict
            await pilot.pause()
    assert app._is_generating is False
    user_msgs = [m for m in app.messages if m.get("role") == "user"]
    assert len(user_msgs) == 1
    assert user_msgs[0]["content"] == "pergunta"


@pytest.mark.asyncio
async def test_run_llm_response_generic_error(app) -> None:
    """Erro genérico → friendly 'Erro inesperado'."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        raise RuntimeError("weird internal failure")
        yield  # pragma: no cover

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.MessageWidget.query_one", return_value=MagicMock()) as mock_q:
            await app.run_llm_response("pergunta")
            await pilot.pause()
    assert app._is_generating is False
    assert mock_q.called  # fluxo de erro atualizou o widget


@pytest.mark.asyncio
async def test_run_llm_response_timeout_error(app) -> None:
    """Erro com 'timeout' → friendly de timeout."""
    from unittest.mock import AsyncMock, MagicMock, patch

    async def chat_gen():
        await asyncio.sleep(0)
        raise TimeoutError("request timed out")
        yield  # pragma: no cover

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.chat = MagicMock(return_value=chat_gen())

    app.pending_images = []
    async with app.run_test() as pilot:
        with patch("miru.ui.tui.app.OllamaClient", return_value=client), \
             patch("miru.ui.tui.app.MessageWidget.query_one", return_value=MagicMock()) as mock_q:
            await app.run_llm_response("pergunta")
            await pilot.pause()
    assert app._is_generating is False
    assert mock_q.called


@pytest.mark.asyncio
async def test_prompt_input_arrow_keys_history(app) -> None:
    """Seta ↑/↓ no PromptInput navegam o histórico de inputs."""
    from textual.events import Key

    app._input_history = ["msg1", "msg2"]

    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        # cursor na primeira linha → ↑ navega histórico
        event_up = Key(key="up", character="")
        user_input.on_key(event_up)
        await pilot.pause()
        event_down = Key(key="down", character="")
        user_input.on_key(event_down)
        await pilot.pause()


@pytest.mark.asyncio
async def test_prompt_input_alt_arrows(app) -> None:
    """Alt+↑/↓ navegam entre mensagens."""
    from textual.events import Key

    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        event_alt_up = Key(key="alt+up", character="")
        user_input.on_key(event_alt_up)
        await pilot.pause()
        event_alt_down = Key(key="alt+down", character="")
        user_input.on_key(event_alt_down)
        await pilot.pause()


@pytest.mark.asyncio
async def test_prompt_input_f1_help(app) -> None:
    """F1 no PromptInput abre ajuda."""
    from textual.events import Key

    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        event_f1 = Key(key="f1", character="")
        user_input.on_key(event_f1)
        await pilot.pause()
        assert app.screen_stack


# ── Meta 1: Export modal flow ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_modal_pushes_screen(app) -> None:
    """action_export_session com mensagens → ExportScreen no stack."""
    from miru.ui.tui.export_screen import ExportScreen

    app.messages = [{"role": "user", "content": "olá"}]
    async with app.run_test() as pilot:
        app.action_export_session()
        await pilot.pause()
        assert isinstance(app.screen_stack[-1], ExportScreen)


@pytest.mark.asyncio
async def test_export_modal_dismiss_with_format(app, tmp_path) -> None:
    """Fluxo do modal: dismiss com (fmt, path) → callback _on_export_complete roda export_session."""
    from miru.ui.tui.export_screen import ExportScreen

    app.messages = [{"role": "user", "content": "olá"}]
    app.current_session_name = "conv-teste"
    out = tmp_path / "out.md"
    async with app.run_test() as pilot:
        app.action_export_session()
        await pilot.pause()
        export_screen = app.screen_stack[-1]
        assert isinstance(export_screen, ExportScreen)
        path_input = export_screen.query_one("#path_input")
        assert path_input.value == "conv-teste.md"
        with patch("miru.ui.tui.app.export_session") as mock_export:
            export_screen.dismiss(("markdown", str(out)))
            await pilot.pause()
        mock_export.assert_called_once_with("conv-teste", str(out), "markdown")


@pytest.mark.asyncio
async def test_export_complete_saved_session(app, tmp_path, monkeypatch) -> None:
    """_on_export_complete com sessão salva → export_session chamado."""
    import miru.ui.tui.app as app_mod

    app.messages = [{"role": "user", "content": "x"}]
    app.current_session_name = "conv"
    out = tmp_path / "out.md"
    async with app.run_test() as pilot:
        with patch.object(app_mod, "export_session") as mock_export:
            app._on_export_complete(("markdown", str(out)))
            await pilot.pause()
        mock_export.assert_called_once_with("conv", str(out), "markdown")


@pytest.mark.asyncio
async def test_export_complete_error_notifies(app, monkeypatch) -> None:
    """_on_export_complete com erro → notify de erro."""
    import miru.ui.tui.app as app_mod

    app.messages = [{"role": "user", "content": "x"}]
    app.current_session_name = "conv"
    async with app.run_test() as pilot:
        with patch.object(app, "notify") as mock_notify:
            with patch.object(app_mod, "export_session", side_effect=OSError("boom")):
                app._on_export_complete(("markdown", "/tmp/x.md"))
                await pilot.pause()
        mock_notify.assert_called_once()
        assert "Erro ao exportar" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"


@pytest.mark.asyncio
async def test_export_clipboard_error_notifies(app, monkeypatch) -> None:
    """_export_to_clipboard com falha no clipboard → notify de erro."""
    app.messages = [{"role": "user", "content": "pergunta"}, {"role": "assistant", "content": "resposta"}]
    async with app.run_test() as pilot:
        with patch.object(app, "notify") as mock_notify:
            with patch.object(app, "copy_to_clipboard", side_effect=RuntimeError("boom")):
                app._export_to_clipboard()
                await pilot.pause()
        mock_notify.assert_called_once()
        assert "Erro ao copiar" in mock_notify.call_args[0][0]
        assert mock_notify.call_args[1]["severity"] == "error"


@pytest.mark.asyncio
async def test_export_unsaved_json(app, tmp_path) -> None:
    """_export_unsaved com formato json → arquivo com dados."""
    app.messages = [{"role": "user", "content": "olá"}]
    out = tmp_path / "out.json"
    async with app.run_test() as pilot:
        app._export_unsaved(str(out), "json")
        await pilot.pause()
    import json as _json
    data = _json.loads(out.read_text(encoding="utf-8"))
    assert data["messages"][0]["content"] == "olá"


# ── Meta 1: Submit error path e params inválidos ─────────────────────────────

@pytest.mark.asyncio
async def test_submit_message_error_notifies(app) -> None:
    """action_submit_message com exceção interna → notify de erro (except Exception)."""
    async with app.run_test() as pilot:
        user_input = app.query_one("#user_input")
        user_input.text = "olá"
        with patch.object(app, "run_worker", side_effect=RuntimeError("boom")):
            app.action_submit_message()
            await pilot.pause()
        assert app._is_generating is False
        assert app.messages == []  # rollback: mensagem não ficou na lista


@pytest.mark.asyncio
async def test_get_ui_params_invalid_values(app) -> None:
    """_get_ui_params com inputs inválidos → defaults + notify warning."""
    async with app.run_test() as pilot:
        app.query_one("#input_temp").value = "abc"
        app.query_one("#input_top_p").value = "xyz"
        app.query_one("#input_max_tokens").value = "nope"
        app.query_one("#input_seed").value = "seed!"
        model, temp, top_p, max_tokens, seed, _sys_prompt = app._get_ui_params()
        await pilot.pause()
        assert temp == 0.7
        assert top_p == 0.9
        assert max_tokens is None
        assert seed is None


# ── Meta 1: Edit user message ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_edit_user_message_loads_content(app) -> None:
    """edit_user_message: carrega conteúdo no input e trunca mensagens."""
    from miru.ui.tui.app import UserMessageWidget

    async with app.run_test() as pilot:
        chat_window = app.query_one("#chat_window")
        try:
            app.query_one("#onboarding").remove()
        except Exception:
            pass
        await pilot.pause()
        msg_ref = {"role": "user", "content": "texto original", "_ts": "12:00"}
        app.messages = [msg_ref]
        w = UserMessageWidget("texto original", msg_ref=msg_ref, timestamp="12:00", classes="user-message-widget")
        await chat_window.mount(w)
        await pilot.pause()
        app.edit_user_message(msg_ref)
        await pilot.pause()
        user_input = app.query_one("#user_input")
        assert user_input.text == "texto original"
        assert app.messages == []


@pytest.mark.asyncio
async def test_edit_user_message_not_found(app) -> None:
    """edit_user_message com msg_ref fora de messages → notify."""
    async with app.run_test() as pilot:
        app.edit_user_message({"role": "user", "content": "x"})
        await pilot.pause()
        assert app.messages == []


# ── Meta 1: Delete flow ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_session_no_session_notifies(app) -> None:
    """action_delete_session sem sessão → notify."""
    app.current_session_name = None
    async with app.run_test() as pilot:
        with patch.object(app, "notify") as mock_notify:
            app.action_delete_session()
            await pilot.pause()
        mock_notify.assert_called_once()
        assert "Nenhuma sessão selecionada" in mock_notify.call_args[0][0]


@pytest.mark.asyncio
async def test_confirm_delete_success(app, tmp_path, monkeypatch) -> None:
    """_on_confirm_delete confirmado → sessão deletada e UI limpa."""
    import miru.ui.tui.app as app_mod

    app.current_session_name = "conv"
    app.messages = [{"role": "user", "content": "x"}]
    async with app.run_test() as pilot:
        with patch.object(app_mod, "delete_session", return_value=True):
            app._on_confirm_delete(True)
            await pilot.pause()
        assert app.current_session_name is None
        assert app.messages == []
        assert app._turn_counter == 0


@pytest.mark.asyncio
async def test_rename_session_no_session_notifies(app) -> None:
    """action_rename_session sem sessão → notify."""
    app.current_session_name = None
    async with app.run_test() as pilot:
        with patch.object(app, "notify") as mock_notify:
            app.action_rename_session()
            await pilot.pause()
        mock_notify.assert_called_once()
        assert "Nenhuma sessão selecionada" in mock_notify.call_args[0][0]
