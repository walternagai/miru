from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, Input, ListView, ListItem, Label, Static
from textual.binding import Binding

from miru.ollama.client import OllamaClient
from miru.core.config import resolve_host, resolve_model, get_config

from miru.ollama.client import OllamaClient
from miru.core.config import resolve_host, resolve_model, get_config

class TUIApp(App):
    CSS = """
    Screen {
        background: #1a1b26;
    }

    #main_container {
        layout: horizontal;
    }

    #sidebar {
        width: 30%;
        background: #24283b;
        border-right: solid #414868;
        padding: 1;
    }

    #chat_area {
        width: 50%;
        background: #1a1b26;
        padding: 1;
    }

    #context_panel {
        width: 20%;
        background: #24283b;
        border-left: solid #414868;
        padding: 1;
    }

    .message {
        margin: 1 0;
        padding: 1;
        border: solid #414868;
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
    ]

    def __init__(self, model: str | None = None, host: str | None = None, temperature: float | None = None, top_p: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self.model_override = model
        self.host_override = host
        self.temp_override = temperature
        self.top_p_override = top_p
        self.client: OllamaClient | None = None

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
                yield Static("Carregando...", id="model_params")
                
        with Container(id="input_container"):
            yield Input(placeholder="Digite sua mensagem aqui...", id="user_input")
        yield Footer()

    async def on_mount(self) -> None:
        # Priority: CLI Override -> Resolved value
        self.host = self.host_override or resolve_host()
        self.model = self.model_override or resolve_model() or "llama3"
        self.config = get_config()
        
        # Update params panel
        params_panel = self.query_one("#model_params", Static)
        params_panel.update(
            f"Modelo: {self.model}\n"
            f"Host: {self.host}\n\n"
            f"Temp: {self.temp_override if self.temp_override is not None else self.config.default_temperature or 0.7}\n"
            f"Top-P: {self.top_p_override if self.top_p_override is not None else self.config.default_top_p or 0.9}"
        )

        # Mock sessions for now
        session_list = self.query_one("#session_list", ListView)
        session_list.append(ListItem(Label("Sessão Recente 1")))
        session_list.append(ListItem(Label("Sessão Recente 2")))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.value = ""

        chat_window = self.query_one("#chat_window", Vertical)
        user_msg = Label(user_text, classes="message user_message")
        chat_window.mount(user_msg)
        chat_window.scroll_end(forget_momentum=True)

        self.run_worker(self.run_llm_response(user_text))

    async def run_llm_response(self, prompt: str) -> None:
        chat_window = self.query_one("#chat_window", Vertical)
        bot_msg = Label("...", classes="message bot_message")
        chat_window.mount(bot_msg)
        chat_window.scroll_end(forget_momentum=True)

        try:
            # Use a single persistent client if possible, or context manager
            async with OllamaClient(host=self.host) as client:
                full_response = ""
                messages = [{"role": "user", "content": prompt}]
                
                options = {
                    "temperature": self.temp_override or self.config.default_temperature,
                    "top_p": self.top_p_override or self.config.default_top_p,
                }

                async for chunk in client.chat(model=self.model, messages=messages, options=options):
                    content = chunk.get("message", {}).get("content", "")
                    full_response += content
                    bot_msg.update(full_response)
                    chat_window.scroll_end(forget_momentum=True)
        except Exception as e:
            bot_msg.update(f"Erro: {str(e)}")

    def action_new_chat(self) -> None:
        chat_window = self.query_one("#chat_window", Vertical)
        chat_window.children.clear()
        self.notify("Nova conversa iniciada")

if __name__ == "__main__":
    app = TUIApp()
    app.run()
