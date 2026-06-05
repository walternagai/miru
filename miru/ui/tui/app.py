import asyncio
import json
import re
import unicodedata
from collections import deque
from datetime import datetime
from typing import Any


def _session_id(session_name: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", session_name).encode("ascii", "ignore").decode("ascii")
    )
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in normalized)
    return f"session_{safe}"


def _extract_code_blocks(text: str) -> str:
    pattern = r"```(?:\w*)\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return "\n\n".join(matches) if matches else ""


def _make_session_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    words = [w for w in re.split(r"\W+", normalized) if w and w.isalpha()][:3]
    return "_".join(w.lower() for w in words)[:24] if words else "chat"


def _format_updated(iso: str) -> str:
    """Format ISO timestamp as DD/MM HH:MM for sidebar display."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso[:19])
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return iso[:10]


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    TextArea,
)
from textual.widgets._select import NoSelection
from textual.worker import Worker

from miru.config_manager import CONFIG_DIR
from miru.core.config import get_config, reload_config, resolve_host, resolve_model
from miru.latex_unicode import latex_to_unicode
from miru.ollama.client import OllamaClient
from miru.output.renderer import format_metrics
from miru.session import (
    delete_session,
    export_session,
    list_sessions,
    load_favorites,
    load_session,
    save_favorites,
    save_session,
    toggle_favorite,
)
from miru.ui.tui.config_screen import ConfigScreen
from miru.ui.tui.confirm_screen import ConfirmScreen
from miru.ui.tui.export_screen import ExportScreen
from miru.ui.tui.help_screen import HelpScreen
from miru.ui.tui.image_screen import ImageScreen
from miru.ui.tui.preset_screen import PRESETS, PresetScreen
from miru.ui.tui.rename_screen import RenameScreen


# ── Widgets ──────────────────────────────────────────────────────────────────

class MarkdownWidget(Static):
    def __init__(self, text: str = "", **kwargs: Any) -> None:
        self._raw_text = text
        self._is_streaming = False
        super().__init__(**kwargs)

    def update_text(self, text: str, streaming: bool = False) -> None:
        self._raw_text = latex_to_unicode(text)
        self._is_streaming = streaming
        if streaming:
            self.update(self._raw_text)
        else:
            self.update(Markdown(self._raw_text))

    def on_mount(self) -> None:
        self.update_text(self._raw_text)


class MetricsWidget(Static):
    def __init__(self, text: str = "", **kwargs: Any) -> None:
        self._text = text
        super().__init__(**kwargs)

    def update_metrics(self, text: str) -> None:
        self._text = text
        self.update(self._text)

    def on_mount(self) -> None:
        if self._text:
            self.update(self._text)


class TurnSeparator(Static):
    """Visual divider between conversation turns."""

    def __init__(self, turn_num: int, **kwargs: Any) -> None:
        self._turn_num = turn_num
        super().__init__(**kwargs)

    def on_mount(self) -> None:
        self.update(f" ── {self._turn_num} ──")


class UserMessageWidget(Static):
    """Widget for user messages with an edit button."""

    def __init__(
        self,
        text: str,
        msg_ref: dict[str, Any],
        timestamp: str = "",
        **kwargs: Any,
    ) -> None:
        self._text = text
        self._msg_ref = msg_ref
        self._timestamp = timestamp
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        header = f"Você  {self._timestamp}" if self._timestamp else "Você"
        yield Label(header, classes="user-msg-header")
        yield Label(self._text, classes="user-msg-text")
        with Horizontal(classes="user-actions"):
            yield Button("Editar", id="user_edit_btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "user_edit_btn":
            app = self.app
            if isinstance(app, TUIApp):
                app.edit_user_message(self._msg_ref)
            event.stop()


class MessageWidget(Static):
    """Widget for bot messages with action buttons."""

    def __init__(self, text: str = "", message_id: int = 0, **kwargs: Any) -> None:
        self._text = text
        self._message_id = message_id
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield MarkdownWidget(self._text, classes="message-content")
        with Horizontal(classes="actions"):
            yield Button("Copiar", id=f"copy_{self._message_id}", variant="default")
            yield Button("Copiar Código", id=f"copy_code_{self._message_id}", variant="default")
            yield Button("Regenerar", id=f"regen_{self._message_id}", variant="default")

    def on_mount(self) -> None:
        self.query_one(MarkdownWidget).update_text(self._text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("copy_code_"):
            self._copy_code_to_clipboard()
        elif event.button.id and event.button.id.startswith("copy_"):
            self._copy_to_clipboard()
        elif event.button.id and event.button.id.startswith("regen_"):
            self._regenerate()

    def _copy_code_to_clipboard(self) -> None:
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
        try:
            self.app.copy_to_clipboard(self._text)
            self.app.notify("Mensagem copiada para clipboard")
        except Exception:
            self.app.notify("Erro ao copiar mensagem")

    def _regenerate(self) -> None:
        app = self.app
        if isinstance(app, TUIApp):
            app.regenerate_last_message()


class PromptInput(TextArea):
    """TextArea with extended bindings that delegate to TUIApp."""

    BINDINGS = [
        Binding("ctrl+j", "submit_message", "Enviar", show=True),
        Binding("ctrl+n", "new_chat", "Novo", show=True),
        Binding("ctrl+shift+s", "toggle_sidebar", "Sessões", show=True),
        Binding("ctrl+p", "toggle_context", "Params", show=True),
        Binding("ctrl+y", "copy_last_message", "Copiar", show=True),
        Binding("ctrl+shift+r", "regen_last_message", "Regenerar", show=True),
        Binding("ctrl+q", "quit", "Sair", show=True),
        Binding("ctrl+x", "cancel_generation", "Cancelar", show=False),
        Binding("ctrl+e", "export_session", "Exportar", show=False),
        Binding("ctrl+f", "search_chat", "Buscar", show=False),
        Binding("ctrl+shift+f", "toggle_favorite", "Favorito", show=False),
        Binding("f1", "help", "Ajuda", show=False),
    ]

    def action_submit_message(self) -> None:
        self.app.action_submit_message()

    def action_toggle_sidebar(self) -> None:
        self.app.action_toggle_sidebar()

    def action_new_chat(self) -> None:
        self.app.action_new_chat()

    def action_toggle_context(self) -> None:
        self.app.action_toggle_context()

    def action_copy_last_message(self) -> None:
        self.app.action_copy_last_message()

    def action_regen_last_message(self) -> None:
        self.app.action_regen_last_message()

    def action_cancel_generation(self) -> None:
        self.app.action_cancel_generation()

    def action_export_session(self) -> None:
        self.app.action_export_session()

    def action_search_chat(self) -> None:
        self.app.action_search_chat()

    def action_toggle_favorite(self) -> None:
        self.app.action_toggle_favorite()

    def action_help(self) -> None:
        self.app.action_help()

    def on_key(self, event: Key) -> None:
        app = self.app
        if not isinstance(app, TUIApp):
            return

        if event.key == "ctrl+enter":
            app.action_submit_message()
            event.stop()

        elif event.key == "up":
            # Navigate input history when cursor is on first line
            if self.cursor_location[0] == 0:
                app.action_history_up()
                event.stop()

        elif event.key == "down":
            # Navigate input history when cursor is on last line
            last_row = len(self.document.lines) - 1
            if self.cursor_location[0] >= last_row:
                app.action_history_down()
                event.stop()

        elif event.key == "alt+up":
            app.action_navigate_msg_up()
            event.stop()

        elif event.key == "alt+down":
            app.action_navigate_msg_down()
            event.stop()

        elif event.key == "f1":
            app.action_help()
            event.stop()


# ── Application ───────────────────────────────────────────────────────────────

class TUIApp(App[None]):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("ctrl+n", "new_chat", "Novo Chat", show=False),
        Binding("ctrl+s", "save_session", "Salvar", show=False),
        Binding("ctrl+l", "clear_input", "Limpar Input", show=False),
        Binding("ctrl+shift+l", "clear_chat", "Limpar Chat", show=False),
        Binding("ctrl+k", "open_config", "Config", show=False),
        Binding("ctrl+q", "quit", "Sair", show=False),
        Binding("ctrl+p", "toggle_context", "Parâmetros", show=False),
        Binding("ctrl+r", "reload_sessions", "Recarregar", show=False),
        Binding("f2", "rename_session", "Renomear", show=False),
        Binding("delete", "delete_session", "Deletar", show=False),
        Binding("ctrl+i", "add_image", "Imagem", show=False),
        Binding("ctrl+o", "select_preset", "Presets", show=False),
        Binding("ctrl+z", "zen_mode", "Zen", show=False),
        Binding("ctrl+shift+f", "toggle_favorite", "Favorito", show=False),
        Binding("ctrl+enter", "submit_message", "Enviar", show=False),
        Binding("ctrl+shift+s", "toggle_sidebar", "Sessões", show=False),
        Binding("ctrl+y", "copy_last_message", "Copiar Última", show=False),
        Binding("ctrl+shift+y", "copy_last_code", "Copiar Código", show=False),
        Binding("ctrl+shift+r", "regen_last_message", "Regenerar", show=False),
        Binding("ctrl+x", "cancel_generation", "Cancelar", show=False),
        Binding("ctrl+e", "export_session", "Exportar", show=False),
        Binding("ctrl+f", "search_chat", "Buscar", show=False),
        Binding("f1", "help", "Ajuda", show=False),
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
        self.messages: list[dict[str, Any]] = []
        self.system_prompt: str = ""
        self.available_models: list[tuple[str, str]] = []
        self.message_counter: int = 0
        self.pending_images: list[str] = []
        self.zen_mode: bool = False
        self._session_id_to_name: dict[str, str] = {}

        # Generation control
        self._is_generating: bool = False
        self._current_worker: Worker | None = None

        # Zen mode state preservation
        self._pre_zen_sidebar: bool = False
        self._pre_zen_context: bool = False

        # Input history (Sprint 1 — 2.1)
        self._input_history: deque[str] = deque(maxlen=50)
        self._history_index: int = -1
        self._history_draft: str = ""

        # Conversation turn counter (Sprint 4 — 5.3)
        self._turn_counter: int = 0

        # Session list sort order (Sprint 4 — 4.2)
        self._session_sort: str = "updated"

        # Token stats (Sprint 3 — 5.1)
        self._session_tokens: int = 0
        self._session_tps: float = 0.0

        # Search state (Sprint 3 — 2.2)
        self._search_matches: list[int] = []
        self._search_idx: int = -1

        # Message navigation index (Sprint 3 — 2.4)
        self._nav_msg_idx: int = -1

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_container"):
            with Vertical(id="sidebar"):
                with Horizontal(id="sidebar_header"):
                    yield Static("  Sessões", id="sidebar_title")
                    yield Button("⇅", id="sort_btn", variant="default")
                yield Input(
                    placeholder="  Filtrar...",
                    id="session_filter",
                    classes="session_filter",
                )
                yield ListView(id="session_list")

            with Vertical(id="chat_area"):
                yield Static("", id="chat_header")
                with Horizontal(id="search_container"):
                    yield Input(placeholder="🔍 Buscar no chat...", id="search_input")
                    yield Label("", id="search_count")
                    yield Button("✕", id="search_close_btn", variant="default")
                with VerticalScroll(id="chat_window"):
                    yield Static(
                        "  Bem-vindo ao miru\n\n"
                        "  Ctrl+J Enviar  ·  Ctrl+Shift+S Sessões  ·  Ctrl+P Parâmetros\n"
                        "  Ctrl+N Novo Chat  ·  Ctrl+O Presets  ·  Ctrl+Y Copiar última\n"
                        "  Ctrl+I Imagem  ·  Ctrl+F Buscar  ·  F1 Ajuda  ·  Ctrl+Q Sair",
                        id="onboarding",
                        classes="onboarding_hint",
                    )

            with Vertical(id="context_panel"):
                yield Static("  Modelo & Params", id="context_panel_title")
                yield Vertical(id="params_container")

        with Container(id="input_container"):
            yield Static("", id="pending_images")
            with Horizontal():
                yield PromptInput(id="user_input", classes="prompt_input")
                yield Button("Enviar", id="send_button", variant="primary")
        yield Footer()

    # ── Header / Status bar ───────────────────────────────────────────────────

    def _update_chat_header(self) -> None:
        try:
            header = self.query_one("#chat_header", Static)
            model_name = getattr(self, "model", "—")
            session_name = self.current_session_name or "nova conversa"

            stats = ""
            if self._session_tokens > 0:
                tps_part = f"  ·  {self._session_tps:.1f} t/s" if self._session_tps > 0 else ""
                stats = f"  ·  {self._session_tokens} tokens{tps_part}"

            sort_icon = {"updated": "↓", "name": "A↓", "favorite": "★"}
            sort_label = sort_icon.get(self._session_sort, "↓")

            header.update(
                f"  {model_name}   ·   {session_name}{stats}"
                f"   [dim]ordenação: {sort_label}[/dim]"
            )
        except Exception:
            pass

    # ── Model loading ─────────────────────────────────────────────────────────

    async def _suggest_model_from_prompt(self, system_prompt: str) -> None:
        if not system_prompt or not self.available_models:
            return
        prompt_lower = system_prompt.lower()
        if "code" in prompt_lower or "programming" in prompt_lower or "código" in prompt_lower:
            coder_models = [m for m in self.available_models if "coder" in m[0].lower()]
            if coder_models:
                try:
                    self.query_one("#select_model", Select).value = coder_models[0][0]
                    self.notify(f"Modelo sugerido: {coder_models[0][0]}")
                except Exception:
                    pass

    async def _load_available_models(self) -> None:
        try:
            async with OllamaClient(host=self.host) as client:
                models = await client.list_models()
                self.available_models = [(m["name"], m["name"]) for m in models]
        except Exception as e:
            self.available_models = [(self.model, self.model)] if self.model else []
            self.notify(f"Não foi possível carregar modelos: {e}", severity="warning")

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

    # ── Mount ─────────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        self.host = self.host_override or resolve_host()
        self.model = self.model_override or resolve_model() or "llama3"
        self.config = get_config()
        self._update_chat_header()

        params_container = self.query_one("#params_container", Vertical)

        params_container.mount(Label("Modelo", classes="param_label"))
        model_select: Select[str] = Select([], id="select_model", classes="param_input")
        params_container.mount(model_select)
        await self._load_available_models()

        params_container.mount(Label("Temperature", classes="param_label"))
        temp_val = (
            self.temp_override if self.temp_override is not None
            else (self.config.default_temperature if self.config.default_temperature is not None else 0.7)
        )
        params_container.mount(Input(value=str(temp_val), id="input_temp", classes="param_input"))

        params_container.mount(Label("Top-P", classes="param_label"))
        top_p_val = (
            self.top_p_override if self.top_p_override is not None
            else (self.config.default_top_p if self.config.default_top_p is not None else 0.9)
        )
        params_container.mount(Input(value=str(top_p_val), id="input_top_p", classes="param_input"))

        params_container.mount(Label("Max Tokens", classes="param_label"))
        max_tokens_val = self.max_tokens_override or self.config.default_max_tokens or 2048
        params_container.mount(
            Input(value=str(max_tokens_val), id="input_max_tokens", classes="param_input")
        )

        params_container.mount(Label("Seed", classes="param_label"))
        seed_val = (
            self.seed_override
            if self.seed_override is not None
            else (self.config.default_seed or "")
        )
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
        self._update_chat_header()

    # ── Sessions sidebar ──────────────────────────────────────────────────────

    def refresh_sessions(self) -> None:
        session_list = self.query_one("#session_list", ListView)
        sessions = list_sessions()

        # Apply sort
        if self._session_sort == "name":
            sessions.sort(key=lambda x: x["name"].lower())
        elif self._session_sort == "favorite":
            favs = load_favorites()
            sessions.sort(key=lambda x: (x["name"] not in favs, x.get("updated", "")))
        # default "updated" is already sorted by list_sessions()

        session_names = {s["name"] for s in sessions}
        favorites = load_favorites()

        new_mapping: dict[str, str] = {_session_id(s["name"]): s["name"] for s in sessions}

        for child in list(session_list.children):
            if isinstance(child, ListItem) and child.id:
                real_name = self._session_id_to_name.get(child.id)
                if real_name and real_name not in session_names:
                    child.remove()

        self._session_id_to_name = new_mapping
        existing_ids = {child.id for child in session_list.children if child.id}

        for s in sessions:
            session_id = _session_id(s["name"])
            if session_id not in existing_ids:
                prefix = "★ " if s["name"] in favorites else "  "
                turns = s.get("turns", 0)
                updated = _format_updated(s.get("updated", ""))
                meta = f"  {turns} turnos  ·  {updated}" if updated else f"  {turns} turnos"

                item = ListItem(
                    Vertical(
                        Label(f"{prefix}{s['name']}", classes="session-name"),
                        Label(meta, classes="session-meta"),
                    ),
                    id=session_id,
                )
                session_list.append(item)

    def _full_refresh_sessions(self) -> None:
        """Full rebuild of session list (used after sort changes)."""
        session_list = self.query_one("#session_list", ListView)
        for child in list(session_list.children):
            child.remove()
        self._session_id_to_name = {}
        self.refresh_sessions()

    def action_cycle_sort(self) -> None:
        order = ["updated", "name", "favorite"]
        idx = order.index(self._session_sort) if self._session_sort in order else 0
        self._session_sort = order[(idx + 1) % len(order)]
        label = {"updated": "data", "name": "nome", "favorite": "favoritos"}
        self.notify(f"Ordenação: {label[self._session_sort]}")
        self._full_refresh_sessions()
        self._update_chat_header()

    def action_toggle_favorite(self) -> None:
        if not self.current_session_name:
            self.notify("Nenhuma sessão selecionada")
            return
        is_now_favorite = toggle_favorite(self.current_session_name)
        self.refresh_sessions()
        status = "favoritada" if is_now_favorite else "desfavoritada"
        self.notify(f"Sessão '{self.current_session_name}' {status}")

    def action_toggle_context(self) -> None:
        self.query_one("#context_panel").toggle_class("visible")

    def filter_sessions(self, filter_text: str) -> None:
        session_list = self.query_one("#session_list", ListView)
        filter_lower = filter_text.lower().strip()
        for child in session_list.children:
            if isinstance(child, ListItem) and child.id:
                if filter_lower:
                    real_name = self._session_id_to_name.get(child.id, child.id)
                    child.set_class(filter_lower not in real_name.lower(), "hidden")
                else:
                    child.remove_class("hidden")

    def _debounced_filter_sessions(self, filter_text: str, delay: float = 0.15) -> None:
        async def _filter() -> None:
            await asyncio.sleep(delay)
            self.filter_sessions(filter_text)

        self.run_worker(_filter(), exclusive=True)

    # ── Presets ───────────────────────────────────────────────────────────────

    def _on_preset_selected(self, preset_name: str | None) -> None:
        if preset_name and preset_name in PRESETS:
            preset = PRESETS[preset_name]
            self.query_one("#input_temp", Input).value = str(preset["temperature"])
            self.query_one("#input_top_p", Input).value = str(preset["top_p"])
            self.query_one("#system_prompt_area", TextArea).text = preset["system_prompt"]
            self.notify(f"Preset '{preset_name}' aplicado")

    def action_select_preset(self) -> None:
        self.push_screen(PresetScreen(), callback=self._on_preset_selected)

    # ── Zen mode ──────────────────────────────────────────────────────────────

    def action_zen_mode(self) -> None:
        self.zen_mode = not self.zen_mode
        sidebar = self.query_one("#sidebar", Vertical)
        context_panel = self.query_one("#context_panel", Vertical)

        if self.zen_mode:
            self._pre_zen_sidebar = sidebar.has_class("visible")
            self._pre_zen_context = context_panel.has_class("visible")
            sidebar.remove_class("visible")
            context_panel.remove_class("visible")
            self.notify("Modo Zen ativado (Ctrl+Z para sair)")
        else:
            if self._pre_zen_sidebar:
                sidebar.add_class("visible")
            if self._pre_zen_context:
                context_panel.add_class("visible")
            self.notify("Modo Zen desativado")

    # ── UI params ─────────────────────────────────────────────────────────────

    def _get_ui_params(self) -> tuple[str, float, float, int | None, int | None, str]:
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
        system_prompt = self.query_one("#system_prompt_area", TextArea).text.strip()

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
            self.notify("Parâmetros inválidos — usando valores padrão", severity="warning")

        return current_model, current_temp, current_top_p, current_max_tokens, current_seed, system_prompt

    def _build_chat_history(
        self,
        prompt: str,
        system_prompt: str,
        encoded_images: list[str] | None = None,
        include_new_user_msg: bool = True,
    ) -> list[dict[str, Any]]:
        # Strip metadata keys (prefixed with _) before sending to API
        chat_history = [
            {k: v for k, v in msg.items() if not k.startswith("_")}
            for msg in self.messages
        ]

        if system_prompt and not any(msg.get("role") == "system" for msg in chat_history):
            chat_history.insert(0, {"role": "system", "content": system_prompt})

        if include_new_user_msg:
            user_msg: dict[str, Any] = {"role": "user", "content": prompt}
            if encoded_images:
                user_msg["images"] = encoded_images
            chat_history.append(user_msg)

        return chat_history

    # ── LLM response ──────────────────────────────────────────────────────────

    async def run_llm_response(
        self,
        prompt: str,
        user_msg_dict: dict[str, Any] | None = None,
        skip_user_append: bool = False,
    ) -> None:
        self._is_generating = True
        chat_window = self.query_one("#chat_window", VerticalScroll)

        self.message_counter += 1
        bot_msg = MessageWidget("", message_id=self.message_counter, classes="bot_message")
        chat_window.mount(bot_msg)

        stream_status = Static("⠋  conectando...", classes="stream_status")
        chat_window.mount(stream_status)
        chat_window.scroll_end()

        try:
            self.query_one("#send_button", Button).disabled = True
        except Exception:
            pass

        try:
            current_model, current_temp, current_top_p, current_max_tokens, current_seed, system_prompt = (
                self._get_ui_params()
            )

            # Encode images once — reused for API call and session save
            encoded_images: list[str] | None = None
            if self.pending_images:
                from miru.input.image import encode_images
                try:
                    encoded_images = encode_images(self.pending_images)
                except Exception as img_err:
                    self.notify(f"Imagens ignoradas — erro ao processar: {img_err}", severity="warning")

            final_chunk = None
            full_response = ""
            last_update = 0.0
            update_interval = 0.05
            chunk_count = 0
            spinner_frame = 0
            stream_start = asyncio.get_running_loop().time()

            try:
                chat_history = self._build_chat_history(
                    prompt, system_prompt, encoded_images,
                    include_new_user_msg=not skip_user_append,
                )
            except Exception:
                return

            options: dict[str, Any] = {"temperature": current_temp, "top_p": current_top_p}
            if current_max_tokens:
                options["num_predict"] = current_max_tokens
            if current_seed is not None:
                options["seed"] = current_seed

            frame = SPINNER_FRAMES[spinner_frame % len(SPINNER_FRAMES)]
            stream_status.update(f"{frame}  {current_model}  ·  gerando...  [Ctrl+X para cancelar]")

            async with OllamaClient(host=self.host) as client:
                tool_manager = None
                if self.enable_tools or self.enable_tavily:
                    from miru.tool_integration import create_tool_manager, execute_tool_loop
                    tool_manager = create_tool_manager(
                        enable_tools=self.enable_tools,
                        enable_tavily=self.enable_tavily,
                        sandbox_dir=self.sandbox_dir,
                        tool_mode=self.tool_mode,
                    )

                if tool_manager:
                    stream_status.update(f"⟳  {current_model}  ·  executando ferramentas...")
                    full_response = await execute_tool_loop(
                        client=client,
                        model=current_model,
                        messages=chat_history,
                        tool_manager=tool_manager,
                        options=options,
                        quiet=True,
                    )
                    bot_msg.query_one(MarkdownWidget).update_text(full_response, streaming=False)
                    chat_window.scroll_end()
                else:
                    async for chunk in client.chat(
                        model=current_model, messages=chat_history, options=options
                    ):
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_response += content
                            chunk_count += len(content.split())
                            current_time = asyncio.get_running_loop().time()

                            if current_time - last_update >= update_interval:
                                bot_msg.query_one(MarkdownWidget).update_text(
                                    full_response, streaming=True
                                )
                                elapsed = current_time - stream_start
                                spinner_frame += 1
                                frame = SPINNER_FRAMES[spinner_frame % len(SPINNER_FRAMES)]
                                stream_status.update(
                                    f"{frame}  {current_model}  ·  {chunk_count} tokens  ·  {elapsed:.1f}s"
                                )
                                chat_window.scroll_end()
                                last_update = current_time
                                await asyncio.sleep(0)

                        if chunk.get("done"):
                            final_chunk = chunk

                    bot_msg.query_one(MarkdownWidget).update_text(full_response, streaming=False)
                    chat_window.scroll_end()

            if final_chunk:
                metrics_str = format_metrics(final_chunk)
                if metrics_str:
                    chat_window.mount(MetricsWidget(metrics_str))
                    chat_window.scroll_end()

                # Accumulate session token stats
                eval_count = final_chunk.get("eval_count", 0)
                total_ns = final_chunk.get("total_duration", 0)
                eval_ns = final_chunk.get("eval_duration", 0)
                if eval_count:
                    self._session_tokens += eval_count
                    if eval_ns and eval_ns > 0:
                        self._session_tps = eval_count / (eval_ns / 1e9)
                    elif total_ns and total_ns > 0:
                        self._session_tps = eval_count / (total_ns / 1e9)
                self._update_chat_header()

            # Save messages
            if not skip_user_append:
                if user_msg_dict is not None:
                    if encoded_images:
                        user_msg_dict["images"] = encoded_images
                    self.messages.append(user_msg_dict)
                else:
                    msg: dict[str, Any] = {"role": "user", "content": prompt}
                    if encoded_images:
                        msg["images"] = encoded_images
                    self.messages.append(msg)

            self.messages.append({"role": "assistant", "content": full_response})
            self._clear_pending_images()

            if not self.current_session_name:
                date_str = datetime.now().strftime("%m%d_%H%M")
                self.current_session_name = f"{date_str}_{_make_session_slug(prompt)}"
                self._update_chat_header()

            try:
                await asyncio.to_thread(
                    save_session, self.current_session_name, current_model, self.messages
                )
                self.refresh_sessions()
            except Exception as save_err:
                self.notify(f"Erro ao salvar sessão: {save_err}", severity="error")

        except Exception as e:
            err_lower = str(e).lower()
            if "connection" in err_lower or "refused" in err_lower or "connect" in err_lower:
                friendly = "Servidor não responde. Verifique com `miru status` ou acesse Configurações (Ctrl+K)."
            elif "timeout" in err_lower:
                friendly = "Tempo limite excedido. Aumente o timeout nas Configurações (Ctrl+K)."
            elif "not found" in err_lower or "404" in err_lower:
                friendly = "Modelo não encontrado. Selecione outro no painel de parâmetros (Ctrl+P)."
            elif "model" in err_lower:
                friendly = "Erro no modelo. Verifique com `miru list` se o modelo está disponível."
            else:
                friendly = "Erro inesperado. Tente novamente ou verifique os logs com `miru logs`."
            bot_msg.query_one(MarkdownWidget).update_text(f"**Erro:** {friendly}")
        finally:
            self._is_generating = False
            self._current_worker = None
            try:
                self.query_one("#send_button", Button).disabled = False
            except Exception:
                pass
            stream_status.remove()

    # ── Generation control ────────────────────────────────────────────────────

    def action_cancel_generation(self) -> None:
        if not self._is_generating:
            self.notify("Nenhuma geração em curso")
            return
        if self._current_worker:
            self._current_worker.cancel()
            self._current_worker = None
        self._is_generating = False
        try:
            self.query_one("#send_button", Button).disabled = False
        except Exception:
            pass
        self.notify("Geração cancelada")

    # ── Session actions ───────────────────────────────────────────────────────

    def action_reload_sessions(self) -> None:
        self.refresh_sessions()
        self.notify("Sessões recarregadas")

    def action_clear_input(self) -> None:
        user_input = self.query_one("#user_input", TextArea)
        user_input.text = ""
        user_input.focus()
        self.notify("Input limpo")

    def action_clear_chat(self) -> None:
        if not self.messages:
            self.notify("Nenhuma conversa para limpar")
            return
        self.push_screen(
            ConfirmScreen(
                "Limpar conversa atual?\nO histórico de mensagens será perdido.",
                title="Limpar Conversa",
            ),
            self._on_confirm_clear,
        )

    def _on_confirm_clear(self, confirmed: bool) -> None:
        if not confirmed:
            return
        self.current_session_name = None
        self.messages = []
        self._turn_counter = 0
        self._session_tokens = 0
        self._session_tps = 0.0
        self._nav_msg_idx = -1
        chat_window = self.query_one("#chat_window", VerticalScroll)
        for child in list(chat_window.children):
            child.remove()
        self.notify("Conversa e histórico limpos")

    def action_save_session(self) -> None:
        if not self.messages:
            self.notify("Nenhuma conversa para salvar")
            return
        if not self.current_session_name:
            first_msg = next((m["content"] for m in self.messages if m.get("role") == "user"), "")
            date_str = datetime.now().strftime("%m%d_%H%M")
            self.current_session_name = f"{date_str}_{_make_session_slug(first_msg)}"

        model_select = self.query_one("#select_model", Select)
        selected_value = model_select.value
        current_model = (
            self.model
            if isinstance(selected_value, NoSelection) or selected_value is None
            else str(selected_value)
        )
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
        if not session:
            self.notify("Erro ao carregar sessão")
            return

        self.current_session_name = session.get("name")
        self.messages = session.get("messages", [])
        self.model = session.get("model", self.model)
        self._turn_counter = 0
        self._nav_msg_idx = -1

        chat_window = self.query_one("#chat_window", VerticalScroll)
        for child in list(chat_window.children):
            child.remove()

        for msg in self.messages:
            if msg.get("role") == "system":
                continue

            content = msg.get("content", "")
            ts = msg.get("_ts", "")

            if msg.get("role") == "user":
                self._turn_counter += 1
                chat_window.mount(
                    TurnSeparator(self._turn_counter, classes="turn-separator")
                )
                chat_window.mount(
                    UserMessageWidget(content, msg_ref=msg, timestamp=ts, classes="user-message-widget")
                )
            else:
                self.message_counter += 1
                chat_window.mount(
                    MessageWidget(content, message_id=self.message_counter, classes="bot_message")
                )

        chat_window.scroll_end()
        self._update_chat_header()

        session_list = self.query_one("#session_list", ListView)
        for child in session_list.children:
            if isinstance(child, ListItem):
                child.remove_class("active-session")
        event.item.add_class("active-session")

        self.notify(f"Sessão '{session_name}' carregada")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "session_filter":
            self._debounced_filter_sessions(event.value)
        elif event.input.id == "search_input":
            self._perform_search(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            self._search_next()

    # ── Rename / Delete session ───────────────────────────────────────────────

    def action_rename_session(self) -> None:
        if not self.current_session_name:
            self.notify("Nenhuma sessão selecionada para renomear")
            return
        self.push_screen(RenameScreen(self.current_session_name), callback=self._on_rename_complete)

    def _on_rename_complete(self, new_name: str | None) -> None:
        if new_name and self.current_session_name:
            old_name = self.current_session_name
            if self._rename_session_file(old_name, new_name):
                self.current_session_name = new_name
                self.refresh_sessions()
                self.notify(f"Sessão renomeada para '{new_name}'")
            else:
                self.notify("Erro ao renomear sessão")

    def _rename_session_file(self, old_name: str, new_name: str) -> bool:
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
        self.push_screen(
            ConfirmScreen(
                f"Deletar sessão '{self.current_session_name}'?\nEssa ação não pode ser desfeita.",
                title="Deletar Sessão",
            ),
            self._on_confirm_delete,
        )

    def _on_confirm_delete(self, confirmed: bool) -> None:
        if not confirmed:
            return
        session_name = self.current_session_name
        if not session_name:
            return
        if delete_session(session_name):
            self.current_session_name = None
            self.messages = []
            self._turn_counter = 0
            self._nav_msg_idx = -1
            chat_window = self.query_one("#chat_window", VerticalScroll)
            for child in list(chat_window.children):
                child.remove()
            self.refresh_sessions()
            self.notify(f"Sessão '{session_name}' deletada")
        else:
            self.notify(f"Erro ao deletar sessão '{session_name}'")

    # ── New chat ──────────────────────────────────────────────────────────────

    def action_new_chat(self) -> None:
        self.current_session_name = None
        self.messages = []
        self._turn_counter = 0
        self._session_tokens = 0
        self._session_tps = 0.0
        self._nav_msg_idx = -1
        chat_window = self.query_one("#chat_window", VerticalScroll)
        for child in list(chat_window.children):
            child.remove()
        chat_window.mount(
            Static(
                "  Bem-vindo ao miru\n\n"
                "  Ctrl+J Enviar  ·  Ctrl+Shift+S Sessões  ·  Ctrl+P Parâmetros\n"
                "  Ctrl+N Novo Chat  ·  Ctrl+O Presets  ·  Ctrl+Y Copiar última\n"
                "  Ctrl+I Imagem  ·  Ctrl+F Buscar  ·  F1 Ajuda  ·  Ctrl+Q Sair",
                id="onboarding",
                classes="onboarding_hint",
            )
        )
        self._update_chat_header()
        self.notify("Nova conversa iniciada")

    # ── Config ────────────────────────────────────────────────────────────────

    def action_open_config(self) -> None:
        self.push_screen(ConfigScreen())

    def sync_config_to_ui(self) -> None:
        self.config = reload_config()
        try:
            model_select = self.query_one("#select_model", Select)
            if self.config.default_model:
                model_select.value = self.config.default_model
        except Exception:
            pass
        try:
            if self.config.default_temperature is not None:
                self.query_one("#input_temp", Input).value = str(self.config.default_temperature)
            if self.config.default_top_p is not None:
                self.query_one("#input_top_p", Input).value = str(self.config.default_top_p)
            if self.config.default_max_tokens is not None:
                self.query_one("#input_max_tokens", Input).value = str(self.config.default_max_tokens)
            if self.config.default_seed is not None:
                self.query_one("#input_seed", Input).value = str(self.config.default_seed)
        except Exception:
            pass
        self.notify("Configurações sincronizadas")

    # ── Regenerate ────────────────────────────────────────────────────────────

    def regenerate_last_message(self) -> None:
        if self._is_generating:
            self.notify("Aguarde a resposta atual...", severity="warning")
            return

        last_assistant_idx: int | None = None
        last_user_idx: int | None = None

        for i in range(len(self.messages) - 1, -1, -1):
            role = self.messages[i].get("role")
            if role == "assistant" and last_assistant_idx is None:
                last_assistant_idx = i
            elif role == "user" and last_assistant_idx is not None:
                last_user_idx = i
                break

        if last_user_idx is None or last_assistant_idx is None:
            self.notify("Nenhuma mensagem para regenerar")
            return

        last_user_msg = self.messages[last_user_idx].get("content", "")

        # Remove only the assistant message; keep the user message in self.messages
        self.messages.pop(last_assistant_idx)

        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)

        # Strip trailing MetricsWidgets
        while children and isinstance(children[-1], MetricsWidget):
            children[-1].remove()
            children.pop()

        # Remove only the last bot MessageWidget (keep UserMessageWidget)
        if children and isinstance(children[-1], MessageWidget):
            children[-1].remove()

        self._is_generating = True
        worker = self.run_worker(
            self.run_llm_response(last_user_msg, skip_user_append=True)
        )
        self._current_worker = worker

    # ── Edit user message ─────────────────────────────────────────────────────

    def edit_user_message(self, msg_ref: dict[str, Any]) -> None:
        if self._is_generating:
            self.notify("Aguarde a resposta atual...", severity="warning")
            return

        try:
            idx = next(i for i, m in enumerate(self.messages) if m is msg_ref)
        except StopIteration:
            self.notify("Mensagem não encontrada")
            return

        content = msg_ref.get("content", "")

        # Truncate messages before this user message
        self.messages = self.messages[:idx]

        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)

        found_idx: int | None = None
        for i, child in enumerate(children):
            if isinstance(child, UserMessageWidget) and child._msg_ref is msg_ref:
                found_idx = i
                break

        if found_idx is not None:
            # Also remove the TurnSeparator immediately before this widget
            start_idx = found_idx
            if found_idx > 0 and isinstance(children[found_idx - 1], TurnSeparator):
                start_idx = found_idx - 1

            for widget in children[start_idx:]:
                widget.remove()

            # Recount remaining separators to sync _turn_counter
            remaining = children[:start_idx]
            self._turn_counter = sum(1 for c in remaining if isinstance(c, TurnSeparator))

        user_input = self.query_one("#user_input", TextArea)
        user_input.text = content
        user_input.focus()
        self._history_index = -1
        self.notify("Mensagem carregada para edição")

    # ── Images ────────────────────────────────────────────────────────────────

    def action_add_image(self) -> None:
        self.push_screen(
            ImageScreen(current_count=len(self.pending_images)),
            callback=self._on_image_added,
        )

    def _on_image_added(self, image_path: str | None) -> None:
        if not image_path:
            return
        self.pending_images.append(image_path)
        self._update_pending_images_indicator()
        self.notify(f"Imagem adicionada ({len(self.pending_images)} pendente(s))")

    def _update_pending_images_indicator(self) -> None:
        try:
            indicator = self.query_one("#pending_images", Static)
            if self.pending_images:
                count = len(self.pending_images)
                text = f"  📎 {count} imagem{'ns' if count > 1 else ''} pendente{'s' if count > 1 else ''}"
                indicator.update(text)
                indicator.add_class("has_images")
            else:
                indicator.update("")
                indicator.remove_class("has_images")
        except Exception:
            pass

    def _clear_pending_images(self) -> None:
        self.pending_images = []
        self._update_pending_images_indicator()

    # ── Submit message ────────────────────────────────────────────────────────

    def action_submit_message(self) -> None:
        if self._is_generating:
            self.notify("Aguarde a resposta atual...", severity="warning")
            return

        try:
            user_input = self.query_one("#user_input", TextArea)
            user_text = user_input.text.strip()
            if not user_text:
                return

            user_input.text = ""

            # Track input history
            self._input_history.appendleft(user_text)
            self._history_index = -1
            self._history_draft = ""

            try:
                self.query_one("#onboarding").remove()
            except Exception:
                pass

            ts = datetime.now().strftime("%H:%M")
            user_msg_dict: dict[str, Any] = {"role": "user", "content": user_text, "_ts": ts}

            chat_window = self.query_one("#chat_window", VerticalScroll)

            # Turn separator
            self._turn_counter += 1
            chat_window.mount(TurnSeparator(self._turn_counter, classes="turn-separator"))

            # User message widget
            chat_window.mount(
                UserMessageWidget(
                    user_text, msg_ref=user_msg_dict, timestamp=ts, classes="user-message-widget"
                )
            )
            chat_window.scroll_end()
            self._nav_msg_idx = -1

            self._is_generating = True
            worker = self.run_worker(
                self.run_llm_response(user_text, user_msg_dict=user_msg_dict)
            )
            self._current_worker = worker

        except Exception as e:
            self._is_generating = False
            self.notify(f"Erro ao enviar mensagem: {e}", severity="error")

    # ── Copy / Clipboard ──────────────────────────────────────────────────────

    def action_copy_last_message(self) -> None:
        chat_window = self.query_one("#chat_window", VerticalScroll)
        for child in reversed(list(chat_window.children)):
            if isinstance(child, MessageWidget):
                child._copy_to_clipboard()
                return
        self.notify("Nenhuma mensagem para copiar")

    def action_copy_last_code(self) -> None:
        chat_window = self.query_one("#chat_window", VerticalScroll)
        for child in reversed(list(chat_window.children)):
            if isinstance(child, MessageWidget):
                child._copy_code_to_clipboard()
                return
        self.notify("Nenhuma mensagem para copiar")

    def action_regen_last_message(self) -> None:
        self.regenerate_last_message()

    # ── Sidebar / context toggle ──────────────────────────────────────────────

    def action_toggle_sidebar(self) -> None:
        self.query_one("#sidebar", Vertical).toggle_class("visible")

    # ── Input history (Sprint 1 — 2.1) ───────────────────────────────────────

    def action_history_up(self) -> None:
        if not self._input_history:
            return
        user_input = self.query_one("#user_input", TextArea)
        if self._history_index == -1:
            self._history_draft = user_input.text
        new_idx = self._history_index + 1
        if new_idx < len(self._input_history):
            self._history_index = new_idx
            user_input.text = list(self._input_history)[new_idx]

    def action_history_down(self) -> None:
        if self._history_index == -1:
            return
        user_input = self.query_one("#user_input", TextArea)
        new_idx = self._history_index - 1
        if new_idx < 0:
            self._history_index = -1
            user_input.text = self._history_draft
        else:
            self._history_index = new_idx
            user_input.text = list(self._input_history)[new_idx]

    # ── Search (Sprint 3 — 2.2) ───────────────────────────────────────────────

    def action_search_chat(self) -> None:
        search_container = self.query_one("#search_container")
        is_open = search_container.has_class("visible")
        if is_open:
            search_container.remove_class("visible")
            self._clear_search_highlights()
            self.query_one("#user_input", TextArea).focus()
        else:
            search_container.add_class("visible")
            self.query_one("#search_input", Input).focus()

    def _clear_search_highlights(self) -> None:
        try:
            chat_window = self.query_one("#chat_window", VerticalScroll)
            for child in chat_window.children:
                child.remove_class("search-match")
                child.remove_class("search-current")
        except Exception:
            pass
        self._search_matches = []
        self._search_idx = -1
        self._update_search_count()

    def _perform_search(self, query: str) -> None:
        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)

        for child in children:
            child.remove_class("search-match")
            child.remove_class("search-current")

        if not query.strip():
            self._search_matches = []
            self._search_idx = -1
            self._update_search_count()
            return

        query_lower = query.lower()
        matches: list[int] = []

        for i, child in enumerate(children):
            text = ""
            if isinstance(child, UserMessageWidget):
                text = child._text
            elif isinstance(child, MessageWidget):
                text = child._text
            if text and query_lower in text.lower():
                child.add_class("search-match")
                matches.append(i)

        self._search_matches = matches
        self._search_idx = 0 if matches else -1

        if matches:
            children[matches[0]].add_class("search-current")
            children[matches[0]].scroll_visible()

        self._update_search_count()

    def _search_next(self) -> None:
        if not self._search_matches:
            return
        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)

        if self._search_idx >= 0:
            children[self._search_matches[self._search_idx]].remove_class("search-current")

        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        children[self._search_matches[self._search_idx]].add_class("search-current")
        children[self._search_matches[self._search_idx]].scroll_visible()
        self._update_search_count()

    def _update_search_count(self) -> None:
        try:
            label = self.query_one("#search_count", Label)
            if self._search_matches:
                label.update(f"{self._search_idx + 1}/{len(self._search_matches)}")
            else:
                label.update("0/0")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_close_btn":
            self.action_search_chat()
            event.stop()
        elif event.button.id == "sort_btn":
            self.action_cycle_sort()
            event.stop()

    # ── Message navigation (Sprint 3 — 2.4) ──────────────────────────────────

    def action_navigate_msg_up(self) -> None:
        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)
        navigable = [
            i for i, c in enumerate(children)
            if isinstance(c, (UserMessageWidget, MessageWidget))
        ]
        if not navigable:
            return

        for child in children:
            child.remove_class("msg-nav-focus")

        if self._nav_msg_idx == -1:
            self._nav_msg_idx = len(navigable) - 1
        else:
            self._nav_msg_idx = max(0, self._nav_msg_idx - 1)

        target = children[navigable[self._nav_msg_idx]]
        target.add_class("msg-nav-focus")
        target.scroll_visible()

    def action_navigate_msg_down(self) -> None:
        chat_window = self.query_one("#chat_window", VerticalScroll)
        children = list(chat_window.children)
        navigable = [
            i for i, c in enumerate(children)
            if isinstance(c, (UserMessageWidget, MessageWidget))
        ]
        if not navigable:
            return

        for child in children:
            child.remove_class("msg-nav-focus")

        if self._nav_msg_idx == -1:
            self._nav_msg_idx = 0
        else:
            self._nav_msg_idx = min(len(navigable) - 1, self._nav_msg_idx + 1)

        target = children[navigable[self._nav_msg_idx]]
        target.add_class("msg-nav-focus")
        target.scroll_visible()

    # ── Help (Sprint 1 — 2.3) ────────────────────────────────────────────────

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    # ── Export (Sprint 2 — 4.3) ───────────────────────────────────────────────

    def action_export_session(self) -> None:
        if not self.messages:
            self.notify("Nenhuma conversa para exportar")
            return
        name = self.current_session_name or "conversa"
        self.push_screen(ExportScreen(session_name=name), callback=self._on_export_complete)

    def _on_export_complete(self, result: tuple[str, str] | None) -> None:
        if not result:
            return
        fmt, path = result

        if fmt == "clipboard":
            self._export_to_clipboard()
            return

        try:
            if self.current_session_name:
                export_session(self.current_session_name, path, fmt)
            else:
                self._export_unsaved(path, fmt)
            self.notify(f"Exportado para {path}")
        except Exception as e:
            self.notify(f"Erro ao exportar: {e}", severity="error")

    def _export_to_clipboard(self) -> None:
        lines = []
        for msg in self.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                continue
            prefix = "Você" if role == "user" else "Assistente"
            lines.append(f"[{prefix}]\n{content}\n")
        try:
            self.copy_to_clipboard("\n".join(lines))
            self.notify("Conversa copiada para clipboard")
        except Exception:
            self.notify("Erro ao copiar para clipboard", severity="error")

    def _export_unsaved(self, path: str, fmt: str) -> None:
        """Export when session hasn't been saved to disk yet."""
        import json as _json
        name = self.current_session_name or "conversa"
        session_data = {
            "name": name,
            "model": getattr(self, "model", ""),
            "messages": self.messages,
        }

        if fmt == "json":
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(session_data, f, indent=2, ensure_ascii=False)
        elif fmt in ("markdown", "md"):
            lines = [f"# {name}\n"]
            for msg in self.messages:
                role = msg.get("role", "")
                if role == "system":
                    continue
                lines.append("## Você\n" if role == "user" else "## Assistente\n")
                lines.append(f"{msg.get('content', '')}\n")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        elif fmt == "txt":
            lines = []
            for msg in self.messages:
                role = msg.get("role", "")
                if role == "system":
                    continue
                prefix = "[VOCÊ]" if role == "user" else "[ASSISTENTE]"
                lines.append(f"{prefix}\n{msg.get('content', '')}\n")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))



if __name__ == "__main__":
    app = TUIApp()
    app.run()
