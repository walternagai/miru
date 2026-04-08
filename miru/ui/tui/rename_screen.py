"""Rename session screen for the TUI."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from miru.session import get_session_path


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
            if new_name and new_name != self.session_name:
                if get_session_path(new_name).exists():
                    self.app.notify(f"Erro: Sessão '{new_name}' já existe")
                    return
                self.dismiss(new_name)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "rename_input":
            new_name = event.value.strip()
            if new_name and new_name != self.session_name:
                if get_session_path(new_name).exists():
                    self.app.notify(f"Erro: Sessão '{new_name}' já existe")
                    return
                self.dismiss(new_name)
            else:
                self.dismiss(None)
