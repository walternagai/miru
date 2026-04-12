"""Preset selection screen for model personalities."""

import unicodedata
from typing import TypedDict

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class PresetConfig(TypedDict):
    temperature: float
    top_p: float
    system_prompt: str


PRESETS: dict[str, PresetConfig] = {
    "Preciso": {
        "temperature": 0.3,
        "top_p": 0.9,
        "system_prompt": (
            "Você é um assistente preciso e objetivo. "
            "Responda de forma clara e concisa, focando nos fatos."
        ),
    },
    "Criativo": {
        "temperature": 1.0,
        "top_p": 0.95,
        "system_prompt": (
            "Você é um assistente criativo e imaginativo. "
            "Explore ideias de forma inovadora e divertida."
        ),
    },
    "Programador": {
        "temperature": 0.2,
        "top_p": 0.95,
        "system_prompt": (
            "Você é um assistente especializado em programação. "
            "Forneça código bem estruturado, comentado e siga boas práticas."
        ),
    },
    "Acadêmico": {
        "temperature": 0.4,
        "top_p": 0.9,
        "system_prompt": (
            "Você é um assistente acadêmico. "
            "Responda de forma rigorosa, cite fontes quando relevante "
            "e use terminologia técnica apropriada."
        ),
    },
    "Conversacional": {
        "temperature": 0.8,
        "top_p": 0.92,
        "system_prompt": (
            "Você é um assistente amigável e conversacional. "
            "Engaje de forma natural, seja prestativo e mantenha um tom caloroso."
        ),
    },
}


def _preset_id(preset_name: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", preset_name).encode("ascii", "ignore").decode("ascii")
    )
    return f"preset_{normalized.lower()}"


class PresetScreen(ModalScreen[str | None]):
    """Modal screen for selecting personality presets."""

    CSS = """
    PresetScreen {
        align: center middle;
    }

    #preset_dialog {
        width: 60;
        max-width: 80;
        height: auto;
        background: #24283b;
        border: thick #7aa2f7;
        padding: 1;
    }

    #preset_title {
        text-align: center;
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    #preset_list {
        height: auto;
    }

    .preset_button {
        width: 100%;
        margin-bottom: 1;
        background: #3b4261;
        color: #c0caf5;
        border: none;
    }

    .preset_button:hover {
        background: #565f89;
    }

    .preset_description {
        color: #565f89;
        text-style: italic;
        margin-bottom: 1;
    }

    #cancel_button {
        width: 100%;
        background: #565f89;
        color: #c0caf5;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="preset_dialog"):
            yield Label("Personalidade do Modelo", id="preset_title")
            with Vertical(id="preset_list"):
                for idx, preset_name in enumerate(PRESETS, start=1):
                    yield Button(
                        f"[{idx}] {preset_name}\n{self._get_short_desc(preset_name)}",
                        id=_preset_id(preset_name),
                        classes="preset_button",
                    )
            yield Button("[Esc] Cancelar", id="cancel_button")

    def _get_short_desc(self, preset_name: str) -> str:
        descriptions = {
            "Preciso": "Temperatura baixa, respostas objetivas",
            "Criativo": "Temperatura alta, exploração livre",
            "Programador": "Foco em código, máxima precisão",
            "Acadêmico": "Rigor técnico, citações",
            "Conversacional": "Tom amigável e natural",
        }
        return descriptions.get(preset_name, "")

    def on_key(self, event: object) -> None:
        from textual.events import Key
        if not isinstance(event, Key):
            return
        preset_names = list(PRESETS.keys())
        if event.character and event.character.isdigit():
            idx = int(event.character) - 1
            if 0 <= idx < len(preset_names):
                self.dismiss(preset_names[idx])
        elif event.key == "escape":
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_button":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("preset_"):
            for preset_name in PRESETS:
                if event.button.id == _preset_id(preset_name):
                    self.dismiss(preset_name)
                    break
