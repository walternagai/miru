from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Input, ListView, ListItem, Label, Static
from textual.binding import Binding

from miru.ollama.client import OllamaClient
from miru.core.config import resolve_host, resolve_model, get_config
from miru.session import list_sessions, load_session, save_session


class TUIApp(App):
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
    """

    BINDINGS = [
        Binding("ctrl+n", "new_chat", "New Chat"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+p", "toggle_context", "Toggle Panel"),
    ]

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_override = model
        self.host_override = host
        self.temp_override = temperature
        self.top_p_override = top_p
        self.client: OllamaClient | None = None
        self.current_session_name: str | None = None
        self.messages: list[dict[str, str]] = []

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
        # Priority: CLI Override -> Resolved value
        self.host = self.host_override or resolve_host()
        self.model = self.model_override or resolve_model() or "llama3"
        self.config = get_config()

        # Update params panel with editable inputs
        params_container = self.query_one("#params_container", Vertical)

        # Model Selection
        params_container.mount(Label("Modelo:"))
        model_input = Input(value=self.model, id="input_model")
        params_container.mount(model_input)

        # Temperature Input
        temp_val = self.temp_override or self.config.default_temperature or 0.7
        params_container.mount(Label("Temperature:"))
        params_container.mount(Input(value=str(temp_val), id="input_temp"))

        # Top-P Input
        top_p_val = self.top_p_override or self.config.default_top_p or 0.9
        params_container.mount(Label("Top-P:"))
        params_container.mount(Input(value=str(top_p_val), id="input_top_p"))

        # Host Info
        params_container.mount(Label(f"\nHost: {self.host}"))

        # Load real sessions
        self.refresh_sessions()

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
        bot_msg = Label("...", classes="message bot_message")
        chat_window.mount(bot_msg)
        chat_window.scroll_end()

        try:
            # Resolve current values from TUI inputs
            model_input = self.query_one("#input_model", Input).value
            temp_input = self.query_one("#input_temp", Input).value
            top_p_input = self.query_one("#input_top_p", Input).value

            current_model = model_input if model_input else self.model

            try:
                current_temp = (
                    float(temp_input)
                    if temp_input
                    else self.temp_override or self.config.default_temperature or 0.7
                )
                current_top_p = (
                    float(top_p_input)
                    if top_p_input
                    else self.top_p_override or self.config.default_top_p or 0.9
                )
            except ValueError:
                current_temp = self.temp_override or self.config.default_temperature or 0.7
                current_top_p = self.top_p_override or self.config.default_top_p or 0.9

            async with OllamaClient(host=self.host) as client:
                full_response = ""

                # Construct message history
                chat_history = list(self.messages)
                chat_history.append({"role": "user", "content": prompt})

                options = {
                    "temperature": current_temp,
                    "top_p": current_top_p,
                }

                async for chunk in client.chat(
                    model=current_model, messages=chat_history, options=options
                ):
                    content = chunk.get("message", {}).get("content", "")
                    full_response += content
                    bot_msg.update(full_response)
                    chat_window.scroll_end()

            # Update local history state
            self.messages.append({"role": "user", "content": prompt})
            self.messages.append({"role": "assistant", "content": full_response})

            # Handle session naming and persistence
            if not self.current_session_name:
                import uuid

                self.current_session_name = f"chat_{uuid.uuid4().hex[:8]}"

            save_session(self.current_session_name, current_model, self.messages)
            self.refresh_sessions()

        except Exception as e:
            bot_msg.update(f"Erro: {str(e)}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        session_name = event.item.id
        if not session_name:
            return

        session = load_session(session_name)
        if session:
            self.current_session_name = session.get("name")
            self.messages = session.get("messages", [])
            self.model = session.get("model", self.model)

            # Update UI
            chat_window = self.query_one("#chat_window", Vertical)
            for child in list(chat_window.children):
                child.remove()

            for msg in self.messages:
                if msg.get("role") == "system":
                    continue

                role_class = "user_message" if msg.get("role") == "user" else "bot_message"
                chat_window.mount(Label(msg.get("content", ""), classes=f"message {role_class}"))

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


if __name__ == "__main__":
    app = TUIApp()
    app.run()
