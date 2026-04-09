"""Generic confirmation modal screen for the TUI."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen[bool]):
    """Modal screen for yes/no confirmations before destructive actions."""

    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm_dialog {
        width: 60;
        background: #24283b;
        border: thick #e0af68;
        padding: 2;
    }

    #confirm_title {
        text-align: center;
        color: #e0af68;
        text-style: bold;
        margin-bottom: 1;
    }

    #confirm_message {
        text-align: center;
        color: #a9b1d6;
        margin-bottom: 2;
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
        background: #f7768e;
        color: #1a1b26;
    }

    #cancel_btn {
        background: #565f89;
        color: #c0caf5;
    }
    """

    def __init__(self, message: str, title: str = "Confirmar", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._message = message
        self._title = title

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_dialog"):
            yield Label(self._title, id="confirm_title")
            yield Label(self._message, id="confirm_message")
            with Center(id="button_row"):
                yield Button("Confirmar", id="confirm_btn", variant="error")
                yield Button("Cancelar", id="cancel_btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm_btn")

    def on_key(self, event: Any) -> None:
        if event.key == "escape":
            self.dismiss(False)
