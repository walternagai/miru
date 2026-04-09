import asyncio
import json
import re
import unicodedata
import uuid
from typing import Any


def _session_id(session_name: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", session_name).encode("ascii", "ignore").decode("ascii")
    )
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in normalized)
    return f"session_{safe}"


def _extract_code_blocks(text: str) -> str:
    """Extract all code blocks from text and return them joined by newlines."""
    pattern = r"```(?:\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n".join(matches) if matches else ""


from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Select,
    Static,
    TextArea,
)
from textual.widgets._select import NoSelection

from miru.config_manager import CONFIG_DIR
from miru.core.config import get_config, reload_config, resolve_host, resolve_model
from miru.latex_unicode import latex_to_unicode
from miru.ollama.client import OllamaClient
from miru.output.renderer import format_metrics
from miru.session import (
    delete_session,
    list_sessions,
    load_favorites,
    load_session,
    save_favorites,
    save_session,
    toggle_favorite,
)
from miru.ui.tui.config_screen import ConfigScreen
from miru.ui.tui.preset_screen import PRESETS, PresetScreen
from miru.ui.tui.rename_screen import RenameScreen


class MarkdownWidget(Static):
    DEFAULT_CSS = """
    MarkdownWidget {
        height: auto;
        min-height: 1;
    }
    """

    def __init__(self, text: str = "", **kwargs: Any) -> None:
        self._raw_text = text
        super().__init__(**kwargs)

    def update_text(self, text: str) -> None:
        self._raw_text = latex_to_unicode(text)
        markdown_obj = Markdown(self._raw_text)
        self.update(markdown_obj)

    def on_mount(self) -> None:
        self.update_text(self._raw_text)


class MetricsWidget(Static):
    """Widget to display generation metrics."""

    DEFAULT_CSS = """
    MetricsWidget {
        height: auto;
        color: #565f89;
        text-style: italic;
        margin-top: 0;
        padding: 0 1;
    }
    """

    def __init__(self, text: str = "", **kwargs: Any) -> None:
        self._text = text
        super().__init__(**kwargs)

    def update_metrics(self, text: str) -> None:
        self._text = text
        self.update(self._text)

    def on_mount(self) -> None:
        if self._text:
            self.update(self._text)


class MessageWidget(Static):
    """Widget for bot messages with action buttons."""

    DEFAULT_CSS = """
    MessageWidget {
        margin: 1 0;
        padding: 1;
        border: solid #414868;
        background: #24283b;
    }

    MessageWidget .message-content {
        margin-bottom: 1;
    }

    MessageWidget .actions {
        height: auto;
    }

    MessageWidget Button {
        min-width: 8;
        margin-right: 1;
        background: #3b4261;
        color: #c0caf5;
        border: none;
    }

    MessageWidget Button:hover {
        background: #565f89;
    }
    """

    def __init__(self, text: str = "", message_id: int = 0, **kwargs: Any) -> None:
        self._text = text
        self._message_id = message_id
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        content = MarkdownWidget(self._text, classes="message-content")
        yield content

        with Horizontal(classes="actions"):
            yield Button("Copiar", id=f"copy_{self._message_id}", variant="default")
            yield Button("Copiar Código", id=f"copy_code_{self._message_id}", variant="default")
            yield Button("Regenerar", id=f"regen_{self._message_id}", variant="default")

    def on_mount(self) -> None:
        content = self.query_one(MarkdownWidget)
        content.update_text(self._text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("copy_code_"):
            self._copy_code_to_clipboard()
        elif event.button.id and event.button.id.startswith("copy_"):
            self._copy_to_clipboard()
        elif event.button.id and event.button.id.startswith("regen_"):
            self._regenerate()

    def _copy_code_to_clipboard(self) -> None:
        """Copy only code blocks from message content to clipboard."""
        try:
            code_blocks = _extract_code_blocks(self._text)
            if code_blocks:
                self.app.copy_to_clipboard(code_blocks)
                self.app.notify("Código copiado para clipboard")
            else:
                self.app.notify("Nenhum bloco de código encontrado")
        except Exception:
            self.app.notify("Erro ao copiar código")

    def _copy_to_clipboard(self) -> None:
        """Copy message content to clipboard."""
        try:
            self.app.copy_to_clipboard(self._text)
            self.app.notify("Mensagem copiada para clipboard")
        except Exception:
            self.app.notify("Erro ao copiar mensagem")

    def _regenerate(self) -> None:
        """Request message regeneration."""
        app = self.app
        if isinstance(app, TUIApp):
            app.regenerate_last_message()


class TUIApp(App[None]):
    CSS = """
    Screen {
        background: #1a1b26;
    }

    #main_container {
        layout: horizontal;
    }

    #sidebar {
        width: 18%;
        background: #24283b;
        border-right: solid #414868;
        padding: 1;
    }

    #sidebar.hidden {
        display: none;
    }

    #session_filter {
        margin-bottom: 1;
    }

    #chat_area {
        width: 1fr;
        background: #1a1b26;
        padding: 1;
    }

    #context_panel {
        width: 20%;
        background: #24283b;
        border-left: solid #414868;
        padding: 1;
        overflow-y: scroll;
    }

    #context_panel.hidden {
        display: none;
    }

    .message {
        margin: 1 0;
        padding: 1;
        border: solid #414868;
        width: 100%;
    }

    .user_message {
        background: #3b4261;
        text-align: right;
        margin-bottom: 1;
    }

    .bot_message {
        background: #24283b;
        text-align: left;
        margin-bottom: 1;
    }

    #input_container {
        dock: bottom;
        height: auto;
        padding: 1;
        background: #1a1b26;
        border-top: solid #414868;
    }

    #chat_window {
        height: 100%;
        overflow-y: scroll;
    }

    .param_label {
        color: #7aa2f7;
        text-style: bold;
        margin-top: 1;
    }

    .param_input {
        margin-bottom: 1;
    }

    .param_section {
        margin-bottom: 1;
        padding: 1;
        border-bottom: solid #414868;
    }

    #system_prompt_area {
        height: auto;
        min-height: 3;
        max-height: 8;
    }

    #session_list {
        height: 1fr;
    }

    #preset_button {
        margin-top: 1;
        background: #3b4261;
        color: #c0caf5;
        border: none;
    }

    #preset_button:hover {
        background: #565f89;
    }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_chat", "New Chat"),
        Binding("ctrl+s", "save_session", "Save Session"),
        Binding("ctrl+l", "clear_input", "Clear Input"),
        Binding("ctrl+shift+l", "clear_chat", "Clear Chat"),
        Binding("ctrl+k", "open_config", "Config"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+p", "toggle_context", "Toggle Panel"),
        Binding("ctrl+r", "reload_sessions", "Reload Sessions"),
        Binding("f2", "rename_session", "Rename Session"),
        Binding("delete", "delete_session", "Delete Session"),
        Binding("ctrl+i", "add_image", "Add Image"),
        Binding("ctrl+o", "select_preset", "Presets"),
        Binding("ctrl+z", "zen_mode", "Zen Mode"),
        Binding("ctrl+f", "toggle_favorite", "Toggle Favorite"),
    ]

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
        ctx: int | None = None,
        system_prompt: str | None = None,
        timeout: float | None = None,
        enable_tools: bool = False,
        enable_tavily: bool = False,
        sandbox_dir: str | None = None,
        tool_mode: str = "auto_safe",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.model_override = model
        self.host_override = host
        self.temp_override = temperature
        self.top_p_override = top_p
        self.top_k_override = top_k
        self.max_tokens_override = max_tokens
        self.seed_override = seed
        self.ctx_override = ctx
        self.system_prompt_override = system_prompt
        self.timeout_override = timeout
        self.enable_tools = enable_tools
        self.enable_tavily = enable_tavily
        self.sandbox_dir = sandbox_dir
        self.tool_mode = tool_mode
        self.client: OllamaClient | None = None
        self.current_session_name: str | None = None
        self.messages: list[dict[str, str]] = []
        self.system_prompt: str = ""
        self.available_models: list[tuple[str, str]] = []
        self.message_counter: int = 0
        self.pending_images: list[str] = []
        self.zen_mode: bool = False
        self._session_id_to_name: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_container"):
            with Vertical(id="sidebar"):
                yield Label("Sessões")
                yield Input(
                    placeholder="Filtrar sessões...",
                    id="session_filter",
                    classes="session_filter",
                )
                yield ListView(id="session_list")

            with Vertical(id="chat_area"):
                yield Vertical(id="chat_window")

            with Vertical(id="context_panel"):
                yield Label("Modelo & Params")
                yield Vertical(id="params_container")

        with Container(id="input_container"):
            yield Input(placeholder="Digite sua mensagem aqui...", id="user_input")
        yield Footer()

    async def _suggest_model_from_prompt(self, system_prompt: str) -> None:
        """Suggest model based on system prompt keywords."""
        if not system_prompt or not self.available_models:
            return

        prompt_lower = system_prompt.lower()
        suggested = None

        if "code" in prompt_lower or "programming" in prompt_lower or "código" in prompt_lower:
            coder_models = [m for m in self.available_models if "coder" in m[0].lower()]
            if coder_models:
                suggested = coder_models[0][0]

        if suggested:
            try:
                model_select = self.query_one("#select_model", Select)
                model_select.value = suggested
                self.notify(f"Modelo sugerido: {suggested}")
            except Exception:
                pass

    async def _load_available_models(self) -> None:
        """Load available models from Ollama server and populate the select."""
        try:
            async with OllamaClient(host=self.host) as client:
                models = await client.list_models()
                self.available_models = [(m["name"], m["name"]) for m in models]
        except Exception:
            self.available_models = [(self.model, self.model)]

        try:
            model_select = self.query_one("#select_model", Select)
            model_select.set_options(self.available_models)
            if self.model in [m[0] for m in self.available_models]:
                model_select.value = self.model

            system_prompt_widget = self.query_one("#system_prompt_area", TextArea)
            current_prompt = system_prompt_widget.text.strip()
            if current_prompt:
                await self._suggest_model_from_prompt(current_prompt)
        except Exception:
            pass

    async def on_mount(self) -> None:
        self.host = self.host_override or resolve_host()
        self.model = self.model_override or resolve_model() or "llama3"
        self.config = get_config()

        params_container = self.query_one("#params_container", Vertical)

        params_container.mount(Label("Modelo", classes="param_label"))
        model_select: Select[str] = Select(
            [],
            id="select_model",
            classes="param_input",
        )
        params_container.mount(model_select)
        await self._load_available_models()

        params_container.mount(Label("Temperature", classes="param_label"))
        temp_val = self.temp_override or self.config.default_temperature or 0.7
        params_container.mount(Input(value=str(temp_val), id="input_temp", classes="param_input"))

        params_container.mount(Label("Top-P", classes="param_label"))
        top_p_val = self.top_p_override or self.config.default_top_p or 0.9
        params_container.mount(Input(value=str(top_p_val), id="input_top_p", classes="param_input"))

        params_container.mount(Label("Max Tokens", classes="param_label"))
        max_tokens_val = self.max_tokens_override or self.config.default_max_tokens or 2048
        params_container.mount(
            Input(value=str(max_tokens_val), id="input_max_tokens", classes="param_input")
        )

        params_container.mount(Label("Seed", classes="param_label"))
        seed_val = self.seed_override if self.seed_override is not None else (self.config.default_seed or "")
        params_container.mount(Input(value=str(seed_val), id="input_seed", classes="param_input"))

        params_container.mount(Label("System Prompt", classes="param_label"))
        system_prompt_area = TextArea(id="system_prompt_area", classes="param_input")
        system_prompt_area.placeholder = "System prompt opcional..."
        if self.system_prompt_override:
            system_prompt_area.text = self.system_prompt_override
        params_container.mount(system_prompt_area)

        params_container.mount(Button("Personalidades", id="preset_button", variant="default"))

        params_container.mount(Label(f"\nHost: {self.host}"))

        self.refresh_sessions()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "preset_button":
            self.push_screen(PresetScreen(), callback=self._on_preset_selected)

    def _on_preset_selected(self, preset_name: str | None) -> None:
        if preset_name and preset_name in PRESETS:
            preset = PRESETS[preset_name]

            temp_input = self.query_one("#input_temp", Input)
            temp_input.value = str(preset["temperature"])

            top_p_input = self.query_one("#input_top_p", Input)
            top_p_input.value = str(preset["top_p"])

            system_prompt_area = self.query_one("#system_prompt_area", TextArea)
            system_prompt_area.text = preset["system_prompt"]

            self.notify(f"Preset '{preset_name}' aplicado")

    def action_select_preset(self) -> None:
        self.push_screen(PresetScreen(), callback=self._on_preset_selected)

    def action_zen_mode(self) -> None:
        self.zen_mode = not self.zen_mode
        sidebar = self.query_one("#sidebar", Vertical)
        context_panel = self.query_one("#context_panel", Vertical)

        if self.zen_mode:
            sidebar.add_class("hidden")
            context_panel.add_class("hidden")
            self.notify("Modo Zen ativado (Ctrl+Z para sair)")
        else:
            sidebar.remove_class("hidden")
            context_panel.remove_class("hidden")
            self.notify("Modo Zen desativado")

    def refresh_sessions(self) -> None:
        session_list = self.query_one("#session_list", ListView)

        sessions = list_sessions()
        session_names = {s["name"] for s in sessions}
        favorites = load_favorites()

        # Build new mapping
        new_mapping: dict[str, str] = {_session_id(s["name"]): s["name"] for s in sessions}

        # Remove items that no longer exist
        for child in list(session_list.children):
            if isinstance(child, ListItem) and child.id:
                real_name = self._session_id_to_name.get(child.id)
                if real_name and real_name not in session_names:
                    child.remove()

        # Update mapping
        self._session_id_to_name = new_mapping

        # Track existing IDs after removal
        existing_ids = {child.id for child in session_list.children if child.id}

        # Add new sessions
        for s in sessions:
            session_id = _session_id(s["name"])
            if session_id not in existing_ids:
                prefix = "★ " if s["name"] in favorites else "  "
                item = ListItem(Label(f"{prefix}{s['name']}"), id=session_id)
                session_list.append(item)

    def action_toggle_favorite(self) -> None:
        if not self.current_session_name:
            self.notify("Nenhuma sessão selecionada")
            return

        is_now_favorite = toggle_favorite(self.current_session_name)
        self.refresh_sessions()

        status = "favoritada" if is_now_favorite else "desfavoritada"
        self.notify(f"Sessão '{self.current_session_name}' {status}")

    def action_toggle_context(self) -> None:
        panel = self.query_one("#context_panel")
        panel.toggle_class("hidden")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.value = ""

        chat_window = self.query_one("#chat_window", Vertical)
        user_msg = Label(user_text, classes="message user_message")
        chat_window.mount(user_msg)
        chat_window.scroll_end()

        self.run_worker(self.run_llm_response(user_text))

    async def run_llm_response(self, prompt: str) -> None:
        chat_window = self.query_one("#chat_window", Vertical)
        self.message_counter += 1
        bot_msg = MessageWidget("...", message_id=self.message_counter, classes="bot_message")
        chat_window.mount(bot_msg)
        loading = LoadingIndicator()
        chat_window.mount(loading)
        chat_window.scroll_end()

        metrics_widget = None

        try:
            model_select = self.query_one("#select_model", Select)
            selected_value = model_select.value
            if isinstance(selected_value, NoSelection) or selected_value is None:
                current_model = self.model
            else:
                current_model = str(selected_value)

            temp_input = self.query_one("#input_temp", Input).value
            top_p_input = self.query_one("#input_top_p", Input).value
            max_tokens_input = self.query_one("#input_max_tokens", Input).value
            seed_input = self.query_one("#input_seed", Input).value
            system_prompt_widget = self.query_one("#system_prompt_area", TextArea)
            system_prompt = system_prompt_widget.text.strip()

            try:
                current_temp = float(temp_input) if temp_input else 0.7
                current_top_p = float(top_p_input) if top_p_input else 0.9
                current_max_tokens = int(max_tokens_input) if max_tokens_input else None
                current_seed = int(seed_input) if seed_input else None
            except ValueError:
                current_temp = 0.7
                current_top_p = 0.9
                current_max_tokens = None
                current_seed = None

            final_chunk = None

            async with OllamaClient(host=self.host) as client:
                full_response = ""

                chat_history = list(self.messages)

                if system_prompt and not any(msg.get("role") == "system" for msg in chat_history):
                    chat_history.insert(0, {"role": "system", "content": system_prompt})

                chat_history.append({"role": "user", "content": prompt})

                options: dict[str, Any] = {
                    "temperature": current_temp,
                    "top_p": current_top_p,
                }
                if current_max_tokens:
                    options["num_predict"] = current_max_tokens
                if current_seed is not None:
                    options["seed"] = current_seed

                async for chunk in client.chat(
                    model=current_model, messages=chat_history, options=options
                ):
                    content = chunk.get("message", {}).get("content", "")
                    full_response += content
                    content_widget = bot_msg.query_one(MarkdownWidget)
                    content_widget.update_text(full_response)
                    chat_window.scroll_end()

                    if chunk.get("done"):
                        final_chunk = chunk

            if final_chunk:
                metrics_str = format_metrics(final_chunk)
                if metrics_str:
                    metrics_widget = MetricsWidget(metrics_str)
                    chat_window.mount(metrics_widget)
                    chat_window.scroll_end()

            self.messages.append({"role": "user", "content": prompt})
            self.messages.append({"role": "assistant", "content": full_response})

            if not self.current_session_name:
                self.current_session_name = f"chat_{uuid.uuid4().hex[:8]}"

            # Save session in background to avoid blocking UI
            await asyncio.to_thread(
                save_session, self.current_session_name, current_model, self.messages
            )
            self.refresh_sessions()

        except Exception as e:
            bot_msg._text = f"**Erro:** {str(e)}"
            content_widget = bot_msg.query_one(MarkdownWidget)
            content_widget.update_text(f"**Erro:** {str(e)}")
        finally:
            loading.remove()

    def action_reload_sessions(self) -> None:
        self.refresh_sessions()
        self.notify("Sessões recarregadas")

    def action_clear_input(self) -> None:
        user_input = self.query_one("#user_input", Input)
        user_input.value = ""
        user_input.focus()
        self.notify("Input limpo")

    def action_clear_chat(self) -> None:
        self.current_session_name = None
        self.messages = []
        chat_window = self.query_one("#chat_window", Vertical)
        for child in list(chat_window.children):
            child.remove()
        self.notify("Conversa e histórico limpos")

    def action_save_session(self) -> None:
        if not self.messages:
            self.notify("Nenhuma conversa para salvar")
            return

        if not self.current_session_name:
            self.current_session_name = f"chat_{uuid.uuid4().hex[:8]}"

        model_select = self.query_one("#select_model", Select)
        selected_value = model_select.value
        if isinstance(selected_value, NoSelection) or selected_value is None:
            current_model = self.model
        else:
            current_model = str(selected_value)

        save_session(self.current_session_name, current_model, self.messages)
        self.refresh_sessions()
        self.notify(f"Sessão '{self.current_session_name}' salva")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        session_id = event.item.id
        if not session_id:
            return

        session_name = self._session_id_to_name.get(session_id)
        if not session_name:
            return

        session = load_session(session_name)
        if session:
            self.current_session_name = session.get("name")
            self.messages = session.get("messages", [])
            self.model = session.get("model", self.model)

            chat_window = self.query_one("#chat_window", Vertical)
            for child in list(chat_window.children):
                child.remove()

            for msg in self.messages:
                if msg.get("role") == "system":
                    continue

                role_class = "user_message" if msg.get("role") == "user" else "bot_message"
                content = msg.get("content", "")

                if msg.get("role") == "user":
                    chat_window.mount(Label(content, classes=f"message {role_class}"))
                else:
                    self.message_counter += 1
                    chat_window.mount(
                        MessageWidget(
                            content, message_id=self.message_counter, classes="bot_message"
                        )
                    )

            chat_window.scroll_end()
            self.notify(f"Sessão '{session_name}' carregada")
        else:
            self.notify("Erro ao carregar sessão")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "session_filter":
            self._debounced_filter_sessions(event.value)

    def filter_sessions(self, filter_text: str) -> None:
        """Filter sessions by name."""
        session_list = self.query_one("#session_list", ListView)

        filter_lower = filter_text.lower().strip()

        for child in session_list.children:
            if isinstance(child, ListItem) and child.id:
                if filter_lower:
                    real_name = self._session_id_to_name.get(child.id, child.id)
                    visible = filter_lower in real_name.lower()
                    child.set_class(not visible, "hidden")
                else:
                    child.remove_class("hidden")

    def _debounced_filter_sessions(self, filter_text: str, delay: float = 0.15) -> None:
        """Debounced session filtering to avoid UI lag."""

        async def _filter() -> None:
            await asyncio.sleep(delay)
            self.filter_sessions(filter_text)

        self.run_worker(_filter(), exclusive=True)

    def action_rename_session(self) -> None:
        if not self.current_session_name:
            self.notify("Nenhuma sessão selecionada para renomear")
            return

        self.push_screen(
            RenameScreen(self.current_session_name),
            callback=self._on_rename_complete,
        )

    def _on_rename_complete(self, new_name: str | None) -> None:
        if new_name and self.current_session_name:
            old_name = self.current_session_name

            success = self._rename_session_file(old_name, new_name)
            if success:
                self.current_session_name = new_name
                self.refresh_sessions()
                self.notify(f"Sessão renomeada para '{new_name}'")
            else:
                self.notify("Erro ao renomear sessão")

    def _rename_session_file(self, old_name: str, new_name: str) -> bool:
        """Rename session file on disk."""
        old_session = load_session(old_name)
        if not old_session:
            return False

        sessions_dir = CONFIG_DIR / "sessions"
        old_path = sessions_dir / f"{old_name}.json"
        new_path = sessions_dir / f"{new_name}.json"

        if new_path.exists():
            return False

        old_session["name"] = new_name

        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(old_session, f, indent=2, ensure_ascii=False)

        old_path.unlink(missing_ok=True)

        # Migrate favorites
        favorites = load_favorites()
        if old_name in favorites:
            favorites.discard(old_name)
            favorites.add(new_name)
            save_favorites(favorites)

        return True

    def action_delete_session(self) -> None:
        if not self.current_session_name:
            self.notify("Nenhuma sessão selecionada para deletar")
            return

        session_name = self.current_session_name

        if delete_session(session_name):
            self.current_session_name = None
            self.messages = []

            chat_window = self.query_one("#chat_window", Vertical)
            for child in list(chat_window.children):
                child.remove()

            self.refresh_sessions()
            self.notify(f"Sessão '{session_name}' deletada")
        else:
            self.notify(f"Erro ao deletar sessão '{session_name}'")

    def action_new_chat(self) -> None:
        self.current_session_name = None
        self.messages = []
        chat_window = self.query_one("#chat_window", Vertical)
        for child in list(chat_window.children):
            child.remove()
        self.notify("Nova conversa iniciada")

    def action_open_config(self) -> None:
        self.push_screen(ConfigScreen())

    def sync_config_to_ui(self) -> None:
        """Reload config and update UI parameters after config screen is closed."""
        self.config = reload_config()

        model_select = self.query_one("#select_model", Select)
        default_model = self.config.default_model
        if default_model:
            model_select.value = default_model

        self.notify("Configurações sincronizadas")

    def regenerate_last_message(self) -> None:
        """Regenerate the last assistant response."""
        if len(self.messages) < 2:
            self.notify("Nenhuma mensagem para regenerar")
            return

        last_user_msg = None
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i].get("role") == "user":
                last_user_msg = self.messages[i].get("content")
                break

        if not last_user_msg:
            self.notify("Nenhuma pergunta encontrada")
            return

        self.messages.pop()
        self.messages.pop()

        chat_window = self.query_one("#chat_window", Vertical)
        children = list(chat_window.children)
        if len(children) >= 2:
            children[-1].remove()
            children[-2].remove()

        self.run_worker(self.run_llm_response(last_user_msg))

    def action_add_image(self) -> None:
        """Prompt user to add an image path for multimodal support."""
        self.notify("Funcionalidade de imagem em desenvolvimento. Use o CLI para imagens.")


if __name__ == "__main__":
    app = TUIApp()
    app.run()
