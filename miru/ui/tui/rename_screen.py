"""Rename session screen for the TUI."""

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from miru.session import get_session_path

INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')
MAX_NAME_LENGTH = 100
RESERVED_NAMES = {"con", "prn", "aux", "nul"}


def validate_session_name(name: str) -> tuple[bool, str]:
    """Validate session name.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Nome não pode estar vazio"

    if len(name) > MAX_NAME_LENGTH:
        return False, f"Nome muito longo (máx {MAX_NAME_LENGTH} caracteres)"

    if INVALID_CHARS.search(name):
        return False, "Nome contém caracteres inválidos"

    if name.lower() in RESERVED_NAMES:
        return False, "Nome reservado do sistema"

    return True, ""


class RenameScreen(ModalScreen[str | None]):
    """Modal screen for renaming a session."""

    CSS = """
    RenameScreen {
        align: center middle;
    }

    #rename_dialog {
        width: 60;
        background: #24283b;
        border: thick #7aa2f7;
        padding: 2;
    }

    #rename_title {
        text-align: center;
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    #rename_input {
        margin-bottom: 1;
    }

    #button_row {
        align: center middle;
        height: auto;
    }

    Button {
        margin: 0 2;
        min-width: 10;
    }

    #confirm_btn {
        background: #7aa2f7;
        color: #1a1b26;
    }

    #cancel_btn {
        background: #565f89;
        color: #c0caf5;
    }
    """

    def __init__(self, session_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.session_name = session_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename_dialog"):
            yield Label("Renomear Sessão", id="rename_title")
            yield Label(f"Nome atual: {self.session_name}")
            yield Input(
                value=self.session_name,
                id="rename_input",
                placeholder="Digite o novo nome...",
            )
            with Center(id="button_row"):
                yield Button("Confirmar", id="confirm_btn", variant="primary")
                yield Button("Cancelar", id="cancel_btn", variant="default")

    def on_mount(self) -> None:
        input_widget = self.query_one("#rename_input", Input)
        input_widget.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_btn":
            new_name = self.query_one("#rename_input", Input).value.strip()
            is_valid, error_msg = validate_session_name(new_name)

            if not is_valid:
                self.app.notify(f"Erro: {error_msg}")
                return

            if new_name == self.session_name:
                self.dismiss(None)
                return

            if get_session_path(new_name).exists():
                self.app.notify(f"Erro: Sessão '{new_name}' já existe")
                return

            self.dismiss(new_name)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "rename_input":
            new_name = event.value.strip()
            is_valid, error_msg = validate_session_name(new_name)

            if not is_valid:
                self.app.notify(f"Erro: {error_msg}")
                return

            if new_name == self.session_name:
                self.dismiss(None)
                return

            if get_session_path(new_name).exists():
                self.app.notify(f"Erro: Sessão '{new_name}' já existe")
                return

            self.dismiss(new_name)
