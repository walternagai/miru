"""Image path input screen for multimodal support."""

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from miru.input.image import ImageFormatError, ImageNotFoundError, encode_image


class ImageScreen(ModalScreen[str | None]):
    """Modal screen for adding images to multimodal prompts."""

    CSS = """
    ImageScreen {
        align: center middle;
    }

    #image_dialog {
        width: 70;
        background: #24283b;
        border: thick #bb9af7;
        padding: 2;
    }

    #image_title {
        text-align: center;
        color: #bb9af7;
        text-style: bold;
        margin-bottom: 1;
    }

    #image_input {
        margin-bottom: 1;
    }

    #image_hint {
        color: #565f89;
        text-style: italic;
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

    #add_btn {
        background: #bb9af7;
        color: #1a1b26;
    }

    #cancel_btn {
        background: #565f89;
        color: #c0caf5;
    }
    """

    def __init__(self, current_count: int = 0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._current_count = current_count

    def compose(self) -> ComposeResult:
        with Vertical(id="image_dialog"):
            yield Label("Adicionar Imagem", id="image_title")
            yield Label(
                "Digite o caminho para uma imagem (JPG, PNG, GIF, WEBP)",
                id="image_hint",
            )
            yield Input(
                id="image_input",
                placeholder="/caminho/para/imagem.jpg",
            )
            if self._current_count > 0:
                yield Label(
                    f"Imagens pendentes: {self._current_count}",
                    id="pending_count",
                )
            with Center(id="button_row"):
                yield Button("Adicionar", id="add_btn", variant="primary")
                yield Button("Cancelar", id="cancel_btn", variant="default")

    def on_mount(self) -> None:
        input_widget = self.query_one("#image_input", Input)
        input_widget.focus()

    def _validate_and_encode(self, path_str: str) -> str | None:
        """Validate image path and return base64 string."""
        path_str = path_str.strip()
        if not path_str:
            return None

        path = Path(path_str).expanduser().resolve()

        try:
            return encode_image(path)
        except ImageNotFoundError:
            self.app.notify(f"Arquivo não encontrado: {path}", severity="error")
            return None
        except ImageFormatError as e:
            self.app.notify(str(e), severity="error")
            return None
        except Exception as e:
            self.app.notify(f"Erro ao processar imagem: {e}", severity="error")
            return None

    def _confirm_add(self) -> None:
        input_widget = self.query_one("#image_input", Input)
        path_str = input_widget.value.strip()

        if not path_str:
            self.app.notify("Digite um caminho válido", severity="warning")
            return

        base64_image = self._validate_and_encode(path_str)
        if base64_image:
            self.dismiss(path_str)
        else:
            input_widget.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_btn":
            self._confirm_add()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "image_input":
            self._confirm_add()