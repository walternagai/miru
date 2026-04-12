"""Configuration screen for editing miru config.toml settings."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select
from textual.widgets._select import NoSelection

from miru.core.config import Config, reload_config, save_config


class ConfigScreen(ModalScreen[None]):
    """Modal screen for editing global miru configuration."""

    CSS = """
    ConfigScreen {
        align: center middle;
    }

    #config_dialog {
        width: 80%;
        max-width: 80;
        height: 90%;
        background: #24283b;
        border: thick #7aa2f7;
        padding: 1;
    }

    #config_header {
        text-align: center;
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    #config_sections {
        height: 1fr;
        margin-bottom: 1;
    }

    .config_section {
        margin-bottom: 1;
        padding: 1;
        border-bottom: solid #414868;
    }

    .section_title {
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    .config_field {
        margin-bottom: 1;
    }

    .field_label {
        color: #a9b1d6;
        margin-bottom: 0;
    }

    .field_input {
        margin-bottom: 1;
    }

    #button_row {
        align: center middle;
        height: auto;
    }

    Button {
        margin: 0 2;
        min-width: 12;
    }

    #save_btn {
        background: #7aa2f7;
        color: #1a1b26;
    }

    #cancel_btn {
        background: #565f89;
        color: #c0caf5;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config = reload_config()

    def compose(self) -> ComposeResult:
        with Vertical(id="config_dialog"):
            yield Label("Configurações Globais", id="config_header")
            with VerticalScroll(id="config_sections"):
                with Vertical(classes="config_section"):
                    yield Label("Conexão", classes="section_title")
                    with Vertical(classes="config_field"):
                        yield Label("Host URL:", classes="field_label")
                        yield Input(
                            value=self.config.default_host,
                            id="config_host",
                            classes="field_input",
                            placeholder="http://localhost:11434",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Timeout (segundos):", classes="field_label")
                        yield Input(
                            value=str(self.config.default_timeout),
                            id="config_timeout",
                            classes="field_input",
                            placeholder="30",
                        )

                with Vertical(classes="config_section"):
                    yield Label("Modelo Padrão", classes="section_title")
                    with Vertical(classes="config_field"):
                        yield Label("Modelo:", classes="field_label")
                        yield Input(
                            value=self.config.default_model or "",
                            id="config_model",
                            classes="field_input",
                            placeholder="gemma3:27b-cloud",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Temperature:", classes="field_label")
                        yield Input(
                            value=str(self.config.default_temperature or ""),
                            id="config_temp",
                            classes="field_input",
                            placeholder="0.7",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Top-P:", classes="field_label")
                        yield Input(
                            value=str(self.config.default_top_p or ""),
                            id="config_top_p",
                            classes="field_input",
                            placeholder="0.9",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Max Tokens:", classes="field_label")
                        yield Input(
                            value=str(self.config.default_max_tokens or ""),
                            id="config_max_tokens",
                            classes="field_input",
                            placeholder="2048",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Seed:", classes="field_label")
                        yield Input(
                            value=str(self.config.default_seed or ""),
                            id="config_seed",
                            classes="field_input",
                            placeholder="(vazio para aleatório)",
                        )

                with Vertical(classes="config_section"):
                    yield Label("Preferências", classes="section_title")
                    with Vertical(classes="config_field"):
                        yield Label("Idioma:", classes="field_label")
                        yield Select(
                            [
                                ("Português (BR) — pt_BR", "pt_BR"),
                                ("English (US) — en_US", "en_US"),
                                ("Español — es_ES", "es_ES"),
                            ],
                            value=self.config.language or "pt_BR",
                            id="config_language",
                            classes="field_input",
                        )
                    yield Checkbox(
                        "Habilitar histórico",
                        id="config_history",
                        value=self.config.history_enabled,
                    )
                    yield Checkbox(
                        "Modo verboso",
                        id="config_verbose",
                        value=self.config.verbose,
                    )

                with Vertical(classes="config_section"):
                    yield Label("Ferramentas", classes="section_title")
                    yield Checkbox(
                        "Habilitar tools",
                        id="config_tools",
                        value=self.config.enable_tools,
                    )
                    yield Checkbox(
                        "Habilitar Tavily (web search)",
                        id="config_tavily",
                        value=self.config.enable_tavily,
                    )
                    with Vertical(classes="config_field"):
                        yield Label("Modo de Tools:", classes="field_label")
                        yield Select(
                            [
                                ("auto_safe — aprova ações perigosas", "auto_safe"),
                                ("auto — executa tudo automaticamente", "auto"),
                                ("manual — confirma cada chamada", "manual"),
                            ],
                            value=self.config.tool_mode or "auto_safe",
                            id="config_tool_mode",
                            classes="field_input",
                        )
                    with Vertical(classes="config_field"):
                        yield Label("Sandbox Dir:", classes="field_label")
                        yield Input(
                            value=self.config.sandbox_dir or "",
                            id="config_sandbox",
                            classes="field_input",
                            placeholder="(vazio para desabilitar)",
                        )

            with Horizontal(id="button_row"):
                yield Button("Salvar", id="save_btn", variant="primary")
                yield Button("Cancelar", id="cancel_btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            self._save_config()
        else:
            self.dismiss()

    def _save_config(self) -> None:
        try:
            host = self.query_one("#config_host", Input).value.strip()
            timeout_str = self.query_one("#config_timeout", Input).value.strip()
            model = self.query_one("#config_model", Input).value.strip()
            temp_str = self.query_one("#config_temp", Input).value.strip()
            top_p_str = self.query_one("#config_top_p", Input).value.strip()
            max_tokens_str = self.query_one("#config_max_tokens", Input).value.strip()
            seed_str = self.query_one("#config_seed", Input).value.strip()
            lang_widget = self.query_one("#config_language", Select)
            language = str(lang_widget.value) if not isinstance(lang_widget.value, NoSelection) else "pt_BR"
            history_enabled = self.query_one("#config_history", Checkbox).value
            verbose = self.query_one("#config_verbose", Checkbox).value
            enable_tools = self.query_one("#config_tools", Checkbox).value
            enable_tavily = self.query_one("#config_tavily", Checkbox).value
            tool_mode_widget = self.query_one("#config_tool_mode", Select)
            tool_mode = str(tool_mode_widget.value) if not isinstance(tool_mode_widget.value, NoSelection) else "auto_safe"
            sandbox_dir = self.query_one("#config_sandbox", Input).value.strip()

            # Validation
            if not host:
                self.app.notify("Erro: Host URL é obrigatório")
                return

            timeout = float(timeout_str) if timeout_str else 30.0
            if timeout <= 0:
                self.app.notify("Erro: Timeout deve ser maior que 0")
                return

            temperature = float(temp_str) if temp_str else None
            if temperature is not None and not (0 <= temperature <= 2):
                self.app.notify("Erro: Temperature deve estar entre 0 e 2")
                return

            top_p = float(top_p_str) if top_p_str else None
            if top_p is not None and not (0 <= top_p <= 1):
                self.app.notify("Erro: Top-P deve estar entre 0 e 1")
                return

            max_tokens = int(max_tokens_str) if max_tokens_str else None
            if max_tokens is not None and max_tokens < 1:
                self.app.notify("Erro: Max Tokens deve ser maior que 0")
                return

            seed = int(seed_str) if seed_str else None

            new_config = Config(
                default_host=host,
                default_model=model if model else None,
                default_timeout=timeout,
                default_temperature=temperature,
                default_top_p=top_p,
                default_max_tokens=max_tokens,
                default_seed=seed,
                language=language,
                history_enabled=history_enabled,
                history_max_entries=self.config.history_max_entries,
                verbose=verbose,
                tavily_api_key=self.config.tavily_api_key,
                enable_tools=enable_tools,
                enable_tavily=enable_tavily,
                tool_mode=tool_mode,
                sandbox_dir=sandbox_dir if sandbox_dir else None,
                profiles=self.config.profiles,
                current_profile=self.config.current_profile,
            )

            save_config(new_config)
            self.app.notify("Configurações salvas com sucesso!")
            if hasattr(self.app, "sync_config_to_ui"):
                self.app.sync_config_to_ui()
            self.dismiss()

        except ValueError as e:
            self.app.notify(f"Erro ao salvar: {str(e)}")
