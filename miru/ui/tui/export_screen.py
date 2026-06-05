"""Export conversation screen."""

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet


class ExportScreen(ModalScreen[tuple[str, str] | None]):
    """Modal screen for exporting the current conversation."""

    CSS = """
    ExportScreen {
        align: center middle;
    }

    #export_dialog {
        width: 72;
        height: auto;
        background: #24283b;
        border: thick #9d7cd8;
        padding: 2;
    }

    #export_title {
        text-align: center;
        color: #9d7cd8;
        text-style: bold;
        margin-bottom: 1;
    }

    .export_label {
        color: #a9b1d6;
        margin-top: 1;
        margin-bottom: 0;
    }

    #format_set {
        margin-bottom: 1;
        height: auto;
    }

    #path_input {
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

    #export_btn {
        background: #9d7cd8;
        color: #1a1b26;
    }

    #cancel_btn {
        background: #565f89;
        color: #c0caf5;
    }
    """

    def __init__(self, session_name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._session_name = session_name

    def compose(self) -> ComposeResult:
        default_path = f"{self._session_name}.md"
        with Vertical(id="export_dialog"):
            yield Label("Exportar Conversa", id="export_title")
            yield Label("Formato:", classes="export_label")
            with RadioSet(id="format_set"):
                yield RadioButton("Markdown  (.md)", value=True, id="fmt_md")
                yield RadioButton("Texto simples  (.txt)", id="fmt_txt")
                yield RadioButton("JSON  (.json)", id="fmt_json")
                yield RadioButton("Copiar para clipboard", id="fmt_clip")
            yield Label("Caminho do arquivo:", classes="export_label")
            yield Input(
                value=default_path,
                id="path_input",
                placeholder="caminho/para/arquivo",
            )
            with Center(id="button_row"):
                yield Button("Exportar", id="export_btn", variant="primary")
                yield Button("Cancelar", id="cancel_btn", variant="default")

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        try:
            path_input = self.query_one("#path_input", Input)
            stem = Path(path_input.value).stem or self._session_name
            btn_id = str(event.pressed.id or "")
            ext_map = {"fmt_md": ".md", "fmt_txt": ".txt", "fmt_json": ".json", "fmt_clip": ""}
            ext = ext_map.get(btn_id, ".md")
            if ext:
                path_input.value = f"{stem}{ext}"
            else:
                path_input.value = ""
        except Exception:
            pass

    def _get_format(self) -> str:
        try:
            pressed = self.query_one("#format_set", RadioSet).pressed_button
            if pressed:
                return {
                    "fmt_md": "markdown",
                    "fmt_txt": "txt",
                    "fmt_json": "json",
                    "fmt_clip": "clipboard",
                }.get(str(pressed.id or ""), "markdown")
        except Exception:
            pass
        return "markdown"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "export_btn":
            fmt = self._get_format()
            path = self.query_one("#path_input", Input).value.strip()
            if fmt != "clipboard" and not path:
                self.app.notify("Digite um caminho válido", severity="warning")
                return
            self.dismiss((fmt, path))
        else:
            self.dismiss(None)
