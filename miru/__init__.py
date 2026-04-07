"""Miru - CLI Python para servidor Ollama local.

Miru (見る) significa "ver" ou "olhar" em japonês.
Representa a capacidade de visualizar e interagir com modelos de IA
através de comandos claros e intuitivos.
"""

__version__ = "0.5.0"

# Initialize i18n on import
from miru.core.i18n import init_i18n

init_i18n()

__all__ = ["__version__"]