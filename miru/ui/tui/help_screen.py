"""Keyboard shortcuts help screen."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

SHORTCUT_GROUPS = [
    ("Chat", [
        ("Ctrl+J / Ctrl+Enter", "Enviar mensagem"),
        ("Ctrl+N", "Novo chat"),
        ("Ctrl+Shift+L", "Limpar conversa atual"),
        ("Ctrl+L", "Limpar campo de input"),
        ("Ctrl+Y", "Copiar última resposta"),
        ("Ctrl+Shift+Y", "Copiar código da última resposta"),
        ("Ctrl+Shift+R", "Regenerar última resposta"),
        ("Ctrl+X", "Cancelar geração em curso"),
        ("↑ / ↓  (input vazio)", "Navegar histórico de inputs"),
        ("Alt+↑ / Alt+↓", "Navegar entre mensagens no chat"),
    ]),
    ("Sessões", [
        ("Ctrl+Shift+S", "Mostrar/ocultar painel de sessões"),
        ("Ctrl+S", "Salvar sessão atual"),
        ("F2", "Renomear sessão"),
        ("Delete", "Deletar sessão"),
        ("Ctrl+Shift+F", "Favoritar/desfavoritar sessão"),
        ("Ctrl+R", "Recarregar lista de sessões"),
        ("Ctrl+E", "Exportar conversa"),
        ("⇅  (botão sidebar)", "Alternar ordenação da lista"),
    ]),
    ("Interface", [
        ("Ctrl+P", "Mostrar/ocultar painel de parâmetros"),
        ("Ctrl+F", "Abrir/fechar barra de busca"),
        ("Ctrl+Z", "Modo Zen (ocultar painéis laterais)"),
        ("Ctrl+K", "Configurações globais"),
        ("Ctrl+O", "Personalidades (Presets)"),
        ("Ctrl+I", "Adicionar imagem (multimodal)"),
        ("F1  ou  ?", "Esta ajuda"),
        ("Ctrl+Q", "Sair"),
    ]),
]


class HelpScreen(ModalScreen[None]):
    """Modal screen showing all keyboard shortcuts."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help_dialog {
        width: 85%;
        max-width: 96;
        height: 85%;
        background: #24283b;
        border: thick #7aa2f7;
        padding: 1;
    }

    #help_title {
        text-align: center;
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    #help_scroll {
        height: 1fr;
        margin-bottom: 1;
    }

    .help_group_title {
        color: #e0af68;
        text-style: bold;
        margin-top: 1;
        padding: 0 1;
        background: #1f2335;
        width: 100%;
        height: 1;
    }

    .shortcut_row {
        width: 100%;
        height: 1;
        padding: 0 1;
    }

    .shortcut_key {
        color: #7dcfff;
        width: 32;
    }

    .shortcut_desc {
        color: #a9b1d6;
        width: 1fr;
    }

    #help_close_btn {
        width: 100%;
        background: #3b4261;
        color: #c0caf5;
        border: none;
    }

    #help_close_btn:hover {
        background: #565f89;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help_dialog"):
            yield Label("Atalhos de Teclado — F1 para fechar", id="help_title")
            with VerticalScroll(id="help_scroll"):
                for group_name, shortcuts in SHORTCUT_GROUPS:
                    yield Static(f"  {group_name}", classes="help_group_title")
                    for key, desc in shortcuts:
                        with Horizontal(classes="shortcut_row"):
                            yield Static(f"  {key}", classes="shortcut_key")
                            yield Static(desc, classes="shortcut_desc")
            yield Button("[F1 / Esc] Fechar", id="help_close_btn")

    def on_key(self, event: Key) -> None:
        if event.key in ("escape", "f1"):
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
