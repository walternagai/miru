from typing import Any

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
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

from miru.core.config import get_config, reload_config, resolve_host, resolve_model
from miru.latex_unicode import latex_to_unicode
from miru.ollama.client import OllamaClient
from miru.session import list_sessions, load_session, save_session
from miru.ui.tui.config_screen import ConfigScreen


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


class TUIApp(App[None]):
    CSS = """
    Screen {
        background: #1a1b26;
    }

    #main_container {
        layout: horizontal;
    }

    #sidebar {
        width: 25%;
        background: #24283b;
        border-right: solid #414868;
        padding: 1;
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
    ]

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.model_override = model
        self.host_override = host
        self.temp_override = temperature
        self.top_p_override = top_p
        self.client: OllamaClient | None = None
        self.current_session_name: str | None = None
        self.messages: list[dict[str, str]] = []
        self.system_prompt: str = ""
        self.available_models: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_container"):
            with Vertical(id="sidebar"):
                yield Label("Sessões")
                yield ListView(id="session_list")

            with Vertical(id="chat_area"):
                yield Vertical(id="chat_window")

            with Vertical(id="context_panel"):
                yield Label("Modelo & Params")
                yield Vertical(id="params_container")

        with Container(id="input_container"):
            yield Input(placeholder="Digite sua mensagem aqui...", id="user_input")
        yield Footer()

    async def on_mount(self) -> None:
        self.host = self.host_override or resolve_host()
        self.model = self.model_override or resolve_model() or "llama3"
        self.config = get_config()

        params_container = self.query_one("#params_container", Vertical)

        params_container.mount(Label("Modelo", classes="param_label"))
        await self._load_available_models()
        model_select = Select(
            self.available_models,
            id="select_model",
            classes="param_input",
            value=self.model if self.model in [m[0] for m in self.available_models] else None,
        )
        params_container.mount(model_select)

        params_container.mount(Label("Temperature", classes="param_label"))
        temp_val = self.temp_override or self.config.default_temperature or 0.7
        params_container.mount(Input(value=str(temp_val), id="input_temp", classes="param_input"))

        params_container.mount(Label("Top-P", classes="param_label"))
        top_p_val = self.top_p_override or self.config.default_top_p or 0.9
        params_container.mount(Input(value=str(top_p_val), id="input_top_p", classes="param_input"))

        params_container.mount(Label("Max Tokens", classes="param_label"))
        max_tokens_val = self.config.default_max_tokens or 2048
        params_container.mount(
            Input(value=str(max_tokens_val), id="input_max_tokens", classes="param_input")
        )

        params_container.mount(Label("Seed", classes="param_label"))
        seed_val = self.config.default_seed or ""
        params_container.mount(Input(value=str(seed_val), id="input_seed", classes="param_input"))

        params_container.mount(Label("System Prompt", classes="param_label"))
        system_prompt_area = TextArea(id="system_prompt_area", classes="param_input")
        system_prompt_area.placeholder = "System prompt opcional..."
        params_container.mount(system_prompt_area)

        params_container.mount(Label(f"\nHost: {self.host}"))

        self.refresh_sessions()

    async def _load_available_models(self) -> None:
        """Load available models from Ollama server and populate the select."""
        try:
            async with OllamaClient(host=self.host) as client:
                models = await client.list_models()
                self.available_models = [(m["name"], m["name"]) for m in models]
        except Exception:
            self.available_models = [(self.model, self.model)]

    def refresh_sessions(self) -> None:
        session_list = self.query_one("#session_list", ListView)
        existing_ids = {child.id for child in session_list.children if child.id}

        sessions = list_sessions()
        for s in sessions:
            if s["name"] not in existing_ids:
                item = ListItem(Label(s["name"]), id=s["name"])
                session_list.append(item)

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
        bot_msg = MarkdownWidget("...", classes="message bot_message")
        chat_window.mount(bot_msg)
        loading = LoadingIndicator()
        chat_window.mount(loading)
        chat_window.scroll_end()

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
                current_temp = (
                    float(temp_input)
                    if temp_input
                    else self.temp_override or self.config.default_temperature or 0.7
                )
                current_top_p = (
                    float(top_p_input)
                    if top_p_input
                    else self.temp_override or self.config.default_top_p or 0.9
                )
                current_max_tokens = int(max_tokens_input) if max_tokens_input else None
                current_seed = int(seed_input) if seed_input else None
            except ValueError:
                current_temp = self.temp_override or self.config.default_temperature or 0.7
                current_top_p = self.top_p_override or self.config.default_top_p or 0.9
                current_max_tokens = None
                current_seed = None

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
                    bot_msg.update_text(full_response)
                    chat_window.scroll_end()

            self.messages.append({"role": "user", "content": prompt})
            self.messages.append({"role": "assistant", "content": full_response})

            if not self.current_session_name:
                import uuid

                self.current_session_name = f"chat_{uuid.uuid4().hex[:8]}"

            save_session(self.current_session_name, current_model, self.messages)
            self.refresh_sessions()

        except Exception as e:
            bot_msg.update_text(f"**Erro:** {str(e)}")
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
            import uuid

            self.current_session_name = f"chat_{uuid.uuid4().hex[:8]}"

        model_input = self.query_one("#input_model", Input).value
        current_model = model_input if model_input else self.model

        save_session(self.current_session_name, current_model, self.messages)
        self.refresh_sessions()
        self.notify(f"Sessão '{self.current_session_name}' salva")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        session_name = event.item.id
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
                    chat_window.mount(MarkdownWidget(content, classes=f"message {role_class}"))

            chat_window.scroll_end()
            self.notify(f"Sessão '{session_name}' carregada")
        else:
            self.notify("Erro ao carregar sessão")

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


if __name__ == "__main__":
    app = TUIApp()
    app.run()
