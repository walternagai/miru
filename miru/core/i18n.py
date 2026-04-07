"""Internationalization system for miru CLI.

Supports Portuguese (Brazil), English, and Spanish.
Uses environment variable MIRU_LANG or system locale to determine language.
"""

import locale
import os
from dataclasses import dataclass
from typing import Any

SUPPORTED_LANGUAGES = ["pt_BR", "en_US", "es_ES"]
DEFAULT_LANGUAGE = "en_US"

MESSAGES: dict[str, dict[str, str]] = {
    "en_US": {
        # General errors
        "error.prefix": "Error",
        "error.model_not_found": "Model '{model}' not found.",
        "error.connection_failed": "Failed to connect to '{host}'.",
        "error.invalid_host": "Invalid host URL: '{host}'.",
        "error.timeout": "Request timed out after {seconds} seconds.",
        "error.file_not_found": "File not found: '{path}'.",
        "error.invalid_format": "Invalid format: '{format}'. Use: {valid_formats}.",
        
        # Suggestions
        "suggestion.pull_model": "To download: miru pull {model}",
        "suggestion.pull_vision_model": "Download a vision model: miru pull llava:latest",
        "suggestion.available_vision_models": "Available vision models:\n{models}",
        "suggestion.check_ollama": "Make sure Ollama is running: ollama serve",
        "suggestion.use_vision_model": "Use: miru run {model} \"<prompt>\" --image <file>",
        
        # Success messages
        "success.model_pulled": "Model '{model}' pulled successfully.",
        "success.model_deleted": "Model '{model}' deleted successfully.",
        "success.model_copied": "Model copied to '{new_name}'.",
        "success.config_saved": "Configuration saved.",
        "success.session_saved": "Session saved to '{filename}'.",
        
        # Chat commands
        "chat.commands.help": "Chat Commands:",
        "chat.commands.exit": "Exit session",
        "chat.commands.clear": "Clear history",
        "chat.commands.history": "Show turn count",
        "chat.commands.stats": "Show session statistics",
        "chat.commands.model": "Switch model",
        "chat.commands.system": "Change system prompt",
        "chat.commands.retry": "Retry last prompt",
        "chat.commands.save": "Save conversation",
        "chat.commands.export": "Export (json/md/txt)",
        
        "chat.session_ended": "Session ended · {turns} turn(s) · {model}",
        "chat.total_tokens": "Total: {tokens} tokens · Average speed: {speed:.1f} tok/s",
        "chat.history_cleared": "History cleared.",
        "chat.no_previous_prompt": "No previous prompt to retry.",
        "chat.model_switched": "Model switched to: {model}",
        "chat.system_updated": "System prompt updated.",
        
        # Tools
        "tools.processing": "Processing...",
        "tools.iteration_limit": "Tool iteration limit reached.",
        "tools.tavily_not_configured": "Tavily API key not configured.",
        "tools.tavily_setup": "Configure with: miru config set tavily_api_key tvly-your-key\n"
                            "Or use: export MIRU_TAVILY_API_KEY=tvly-your-key\n"
                            "Get your key at: https://tavily.com",
        
        # Model operations
        "models.empty": "No models found.",
        "models.pull_progress": "Pulling {model}...",
        "models.available": "Available models",
        "models.loaded_vram": "Models loaded in VRAM",
        
        # Config
        "config.current": "Current configuration",
        "config.profile_created": "Profile '{name}' created.",
        "config.profile_switched": "Switched to profile '{name}'.",
        "config.profile_deleted": "Profile '{name}' deleted.",
        "config.reset": "Configuration reset to defaults.",
        
        # Setup wizard
        "setup.welcome": "Welcome to miru setup!",
        "setup.checking_ollama": "Checking Ollama connection...",
        "setup.ollama_running": "Ollama is running.",
        "setup.ollama_not_running": "Ollama is not running. Please start with: ollama serve",
        "setup.choose_model": "Choose default model",
        "setup.configure_history": "Configure prompt history",
        "setup.configure_aliases": "Configure model aliases",
        "setup.complete": "Setup complete!",
        
        # Status
        "status.ollama_running": "Ollama is running at {host}",
        "status.ollama_not_running": "Ollama is not accessible at {host}",
        "status.models_count": "{count} model(s) available",
        
        # Quick commands
        "quick.generating_code": "Generating code...",
        "quick.summarizing": "Summarizing text...",
        "quick.translating": "Translating...",
        "quick.analyzing": "Analyzing...",
        
        # Progress indicators
        "progress.downloading": "Downloading",
        "progress.processing": "Processing",
        "progress.comparing": "Comparing models",
        "progress.batch_processing": "Processing batch",
        
        # Misc
        "prompt.enter": "Enter prompt",
        "prompt.model_required": "Model not specified",
        "prompt.use_specify": "Use: miru {command} <model>",
        "prompt.or_configure": "Or configure default_model: miru config set default_model <model>",
        
        "file.copied_clipboard": "Command copied to clipboard.",
        
        "alias.created": "Alias '{alias}' created for '{model}'.",
        "alias.deleted": "Alias '{alias}' deleted.",
        "alias.not_found": "Alias '{alias}' not found.",
        
        "template.saved": "Template '{name}' saved.",
        "template.deleted": "Template '{name}' deleted.",
        "template.not_found": "Template '{name}' not found.",
        
        "session.exported": "Session exported to '{filename}'.",
        "session.deleted": "Session '{name}' deleted.",
        "session.not_found": "Session '{name}' not found.",
    },
    "pt_BR": {
        # General errors
        "error.prefix": "Erro",
        "error.model_not_found": "Modelo '{model}' não encontrado.",
        "error.connection_failed": "Falha ao conectar em '{host}'.",
        "error.invalid_host": "URL de host inválida: '{host}'.",
        "error.timeout": "Tempo limite excedido após {seconds} segundos.",
        "error.file_not_found": "Arquivo não encontrado: '{path}'.",
        "error.invalid_format": "Formato inválido: '{format}'. Use: {valid_formats}.",
        
        # Suggestions
        "suggestion.pull_model": "Para baixar: miru pull {model}",
        "suggestion.pull_vision_model": "Baixe um modelo com visão: miru pull llava:latest",
        "suggestion.available_vision_models": "Modelos com visão disponíveis:\n{models}",
        "suggestion.check_ollama": "Certifique-se de que o Ollama está rodando: ollama serve",
        "suggestion.use_vision_model": "Use: miru run {model} \"<prompt>\" --image <arquivo>",
        
        # Success messages
        "success.model_pulled": "Modelo '{model}' baixado com sucesso.",
        "success.model_deleted": "Modelo '{model}' deletado com sucesso.",
        "success.model_copied": "Modelo copiado para '{new_name}'.",
        "success.config_saved": "Configuração salva.",
        "success.session_saved": "Sessão salva em '{filename}'.",
        
        # Chat commands
        "chat.commands.help": "Comandos do Chat:",
        "chat.commands.exit": "Encerrar sessão",
        "chat.commands.clear": "Limpar histórico",
        "chat.commands.history": "Mostrar contagem de turnos",
        "chat.commands.stats": "Mostrar estatísticas da sessão",
        "chat.commands.model": "Trocar modelo",
        "chat.commands.system": "Alterar system prompt",
        "chat.commands.retry": "Re-executar último prompt",
        "chat.commands.save": "Salvar conversa",
        "chat.commands.export": "Exportar (json/md/txt)",
        
        "chat.session_ended": "Sessão encerrada · {turns} turno(s) · {model}",
        "chat.total_tokens": "Total: {tokens} tokens · Velocidade média: {speed:.1f} tok/s",
        "chat.history_cleared": "Histórico limpo.",
        "chat.no_previous_prompt": "Nenhum prompt anterior para repetir.",
        "chat.model_switched": "Modelo alterado para: {model}",
        "chat.system_updated": "System prompt atualizado.",
        
        # Tools
        "tools.processing": "Processando...",
        "tools.iteration_limit": "Limite de iterações de tools atingido.",
        "tools.tavily_not_configured": "API key do Tavily não configurada.",
        "tools.tavily_setup": "Configure com: miru config set tavily_api_key tvly-sua-key\n"
                            "Ou use: export MIRU_TAVILY_API_KEY=tvly-sua-key\n"
                            "Obtenha sua key em: https://tavily.com",
        
        # Model operations
        "models.empty": "Nenhum modelo encontrado.",
        "models.pull_progress": "Baixando {model}...",
        "models.available": "Modelos disponíveis",
        "models.loaded_vram": "Modelos carregados na VRAM",
        
        # Config
        "config.current": "Configuração atual",
        "config.profile_created": "Profile '{name}' criado.",
        "config.profile_switched": "Mudado para profile '{name}'.",
        "config.profile_deleted": "Profile '{name}' deletado.",
        "config.reset": "Configuração resetada para defaults.",
        
        # Setup wizard
        "setup.welcome": "Bem-vindo ao setup do miru!",
        "setup.checking_ollama": "Verificando conexão com Ollama...",
        "setup.ollama_running": "Ollama está rodando.",
        "setup.ollama_not_running": "Ollama não está rodando. Inicie com: ollama serve",
        "setup.choose_model": "Escolha o modelo padrão",
        "setup.configure_history": "Configurar histórico de prompts",
        "setup.configure_aliases": "Configurar aliases de modelos",
        "setup.complete": "Setup completo!",
        
        # Status
        "status.ollama_running": "Ollama está rodando em {host}",
        "status.ollama_not_running": "Ollama não está acessível em {host}",
        "status.models_count": "{count} modelo(s) disponível(eis)",
        
        # Quick commands
        "quick.generating_code": "Gerando código...",
        "quick.summarizing": "Resumindo texto...",
        "quick.translating": "Traduzindo...",
        "quick.analyzing": "Analisando...",
        
        # Progress indicators
        "progress.downloading": "Baixando",
        "progress.processing": "Processando",
        "progress.comparing": "Comparando modelos",
        "progress.batch_processing": "Processando lote",
        
        # Misc
        "prompt.enter": "Digite o prompt",
        "prompt.model_required": "Modelo não especificado",
        "prompt.use_specify": "Use: miru {command} <model>",
        "prompt.or_configure": "Ou configure default_model: miru config set default_model <model>",
        
        "file.copied_clipboard": "Comando copiado para a área de transferência.",
        
        "alias.created": "Alias '{alias}' criado para '{model}'.",
        "alias.deleted": "Alias '{alias}' deletado.",
        "alias.not_found": "Alias '{alias}' não encontrado.",
        
        "template.saved": "Template '{name}' salvo.",
        "template.deleted": "Template '{name}' deletado.",
        "template.not_found": "Template '{name}' não encontrado.",
        
        "session.exported": "Sessão exportada para '{filename}'.",
        "session.deleted": "Sessão '{name}' deletada.",
        "session.not_found": "Sessão '{name}' não encontrada.",
    },
    "es_ES": {
        # General errors
        "error.prefix": "Error",
        "error.model_not_found": "Modelo '{model}' no encontrado.",
        "error.connection_failed": "Error al conectar a '{host}'.",
        "error.invalid_host": "URL de host inválida: '{host}'.",
        "error.timeout": "Tiempo de espera agotado después de {seconds} segundos.",
        "error.file_not_found": "Archivo no encontrado: '{path}'.",
        "error.invalid_format": "Formato inválido: '{format}'. Use: {valid_formats}.",
        
        # Suggestions
        "suggestion.pull_model": "Para descargar: miru pull {model}",
        "suggestion.pull_vision_model": "Descargue un modelo con visión: miru pull llava:latest",
        "suggestion.available_vision_models": "Modelos con visión disponibles:\n{models}",
        "suggestion.check_ollama": "Asegúrese de que Ollama esté ejecutándose: ollama serve",
        "suggestion.use_vision_model": "Use: miru run {model} \"<prompt>\" --image <archivo>",
        
        # Success messages
        "success.model_pulled": "Modelo '{model}' descargado exitosamente.",
        "success.model_deleted": "Modelo '{model}' eliminado exitosamente.",
        "success.model_copied": "Modelo copiado a '{new_name}'.",
        "success.config_saved": "Configuración guardada.",
        "success.session_saved": "Sesión guardada en '{filename}'.",
        
        # Chat commands
        "chat.commands.help": "Comandos del Chat:",
        "chat.commands.exit": "Terminar sesión",
        "chat.commands.clear": "Limpiar historial",
        "chat.commands.history": "Mostrar conteo de turnos",
        "chat.commands.stats": "Mostrar estadísticas de sesión",
        "chat.commands.model": "Cambiar modelo",
        "chat.commands.system": "Cambiar system prompt",
        "chat.commands.retry": "Repetir último prompt",
        "chat.commands.save": "Guardar conversación",
        "chat.commands.export": "Exportar (json/md/txt)",
        
        "chat.session_ended": "Sesión terminada · {turns} turno(s) · {model}",
        "chat.total_tokens": "Total: {tokens} tokens · Velocidad promedio: {speed:.1f} tok/s",
        "chat.history_cleared": "Historial limpiado.",
        "chat.no_previous_prompt": "No hay prompt anterior para repetir.",
        "chat.model_switched": "Modelo cambiado a: {model}",
        "chat.system_updated": "System prompt actualizado.",
        
        # Tools
        "tools.processing": "Procesando...",
        "tools.iteration_limit": "Límite de iteraciones de tools alcanzado.",
        "tools.tavily_not_configured": "API key de Tavily no configurada.",
        "tools.tavily_setup": "Configure con: miru config set tavily_api_key tvly-su-key\n"
                            "O use: export MIRU_TAVILY_API_KEY=tvly-su-key\n"
                            "Obtenga su key en: https://tavily.com",
        
        # Model operations
        "models.empty": "Ningún modelo encontrado.",
        "models.pull_progress": "Descargando {model}...",
        "models.available": "Modelos disponibles",
        "models.loaded_vram": "Modelos cargados en VRAM",
        
        # Config
        "config.current": "Configuración actual",
        "config.profile_created": "Profile '{name}' creado.",
        "config.profile_switched": "Cambiado a profile '{name}'.",
        "config.profile_deleted": "Profile '{name}' eliminado.",
        "config.reset": "Configuración restablecida a valores predeterminados.",
        
        # Setup wizard
        "setup.welcome": "¡Bienvenido al setup de miru!",
        "setup.checking_ollama": "Verificando conexión con Ollama...",
        "setup.ollama_running": "Ollama está ejecutándose.",
        "setup.ollama_not_running": "Ollama no está ejecutándose. Inicie con: ollama serve",
        "setup.choose_model": "Elija el modelo predeterminado",
        "setup.configure_history": "Configurar historial de prompts",
        "setup.configure_aliases": "Configurar alias de modelos",
        "setup.complete": "¡Setup completo!",
        
        # Status
        "status.ollama_running": "Ollama está ejecutándose en {host}",
        "status.ollama_not_running": "Ollama no está accesible en {host}",
        "status.models_count": "{count} modelo(s) disponible(s)",
        
        # Quick commands
        "quick.generating_code": "Generando código...",
        "quick.summarizing": "Resumiendo texto...",
        "quick.translating": "Traduciendo...",
        "quick.analyzing": "Analizando...",
        
        # Progress indicators
        "progress.downloading": "Descargando",
        "progress.processing": "Procesando",
        "progress.comparing": "Comparando modelos",
        "progress.batch_processing": "Procesando lote",
        
        # Misc
        "prompt.enter": "Ingrese el prompt",
        "prompt.model_required": "Modelo no especificado",
        "prompt.use_specify": "Use: miru {command} <model>",
        "prompt.or_configure": "O configure default_model: miru config set default_model <model>",
        
        "file.copied_clipboard": "Comando copiado al portapapeles.",
        
        "alias.created": "Alias '{alias}' creado para '{model}'.",
        "alias.deleted": "Alias '{alias}' eliminado.",
        "alias.not_found": "Alias '{alias}' no encontrado.",
        
        "template.saved": "Template '{name}' guardado.",
        "template.deleted": "Template '{name}' eliminado.",
        "template.not_found": "Template '{name}' no encontrado.",
        
        "session.exported": "Sesión exportada a '{filename}'.",
        "session.deleted": "Sesión '{name}' eliminada.",
        "session.not_found": "Sesión '{name}' no encontrada.",
    },
}

_current_language: str = DEFAULT_LANGUAGE


def detect_language() -> str:
    """Detect language from environment.
    
    Precedence:
    1. MIRU_LANG environment variable
    2. LANG environment variable
    3. System locale
    4. Default (en_US)
    """
    lang = os.environ.get("MIRU_LANG", "")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    
    lang = os.environ.get("LANG", "")
    if lang.startswith("pt_BR") or lang.startswith("pt_BR"):
        return "pt_BR"
    if lang.startswith("es") or lang.startswith("es_"):
        return "es_ES"
    
    try:
        sys_lang = locale.getdefaultlocale()[0]
        if sys_lang:
            if sys_lang.startswith("pt_BR"):
                return "pt_BR"
            if sys_lang.startswith("es"):
                return "es_ES"
    except Exception:
        pass
    
    return DEFAULT_LANGUAGE


def set_language(lang: str) -> None:
    """Set the current language.
    
    Args:
        lang: Language code (pt_BR, en_US, es_ES)
    """
    global _current_language
    if lang in SUPPORTED_LANGUAGES:
        _current_language = lang
    else:
        _current_language = DEFAULT_LANGUAGE


def get_language() -> str:
    """Get the current language code."""
    return _current_language


def t(key: str, **kwargs: Any) -> str:
    """Translate a message key to the current language.
    
    Args:
        key: Message key (e.g., "error.model_not_found")
        **kwargs: Format variables for the message
        
    Returns:
        Translated and formatted message
        
    Example:
        >>> set_language("pt_BR")
        >>> t("error.model_not_found", model="gemma3:latest")
        "Modelo 'gemma3:latest' não encontrado."
    """
    messages = MESSAGES.get(_current_language, MESSAGES[DEFAULT_LANGUAGE])
    message = messages.get(key, MESSAGES[DEFAULT_LANGUAGE].get(key, key))
    
    try:
        return message.format(**kwargs)
    except KeyError:
        return message


def init_i18n() -> None:
    """Initialize i18n system with detected language."""
    global _current_language
    _current_language = detect_language()