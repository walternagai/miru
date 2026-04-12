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
        "error.audio_processing": "Error processing audio file '{file}': {error}",
        "error.file_processing": "Error processing file '{path}': {error}",
        "error.system_prompt_file": "Error reading system prompt file: {error}",
        "error.model_no_vision": "Model '{model}' does not support images.",
        "error.available_models": "Available models:",
        "error.more_models": "... and {count} more",

        "audio.transcription": "Audio transcription",
        
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
        "chat.commands.recall": "Recall previous prompt",
        "chat.commands.help_cmd": "Show this help",

        "chat.session_ended": "Session ended · {turns} turn(s) · {model}",
        "chat.recall_title": "Previous Prompts",
        "chat.recall_empty": "No previous prompts found",
        "chat.recall_prompt": "Select prompt to recall (0-{count}) or press Enter to cancel",
        "chat.recall_loaded": "Prompt loaded from {date}",
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
        
        # List table headers
        "list.size": "Size",
        "list.modified": "Modified",
        "list.expires": "Expires",
        
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
        
        # Status command
        "status.connection_failed": "Ollama is not responding at {host}",
        "status.check_running": "Check if Ollama is running: ollama serve",
        "status.accessible": "Ollama is accessible at {host}",
        "status.property": "Property",
        "status.value": "Value",
        "status.online": "Online",
        "status.loaded_vram_count": "Models loaded in VRAM ({count}):",
        "status.no_models_vram": "No models loaded in VRAM",
        "status.connection_error": "Cannot connect to Ollama at {host}",
        "status.timeout_error": "Timeout connecting to Ollama at {host}",
        "status.error_unexpected": "Error: {error}",
        "status.model_unloaded": "Model {model} unloaded",
        "status.stop_error": "Error stopping model: {error}",
        "status.no_models_found": "No models found for '{query}'",
        "status.models_matching": "Models matching '{query}'",
        
        # Config command
        "config.unknown_key": "Unknown config key: {key}",
        "config.valid_keys": "Valid keys: default_host, default_model, default_timeout,",
        "config.valid_keys_more": "  default_temperature, default_max_tokens, default_top_p,",
        "config.valid_keys_more2": "  default_top_k, default_seed, history_enabled,",
        "config.valid_keys_more3": "  history_max_entries, verbose, tavily_api_key,",
        "config.valid_keys_more4": "  enable_tools, enable_tavily, tool_mode, sandbox_dir",
        "config.invalid_boolean": "Invalid boolean value: {value}",
        "config.valid_boolean": "Valid values: true, false, 1, 0, yes, no",
        "config.invalid_tool_mode": "Invalid tool_mode: {value}",
        "config.valid_tool_modes": "Valid values: manual, auto, auto_safe",
        "config.invalid_float": "Invalid float value: {value}",
        "config.invalid_integer": "Invalid integer value: {value}",
        "config.api_key_format_warning": "Warning: API key doesn't match expected format (tvly-...)",
        "config.key_set": "Set {key} = {value}",
        "config.config_file": "Config file: {path}",
        "config.key_value": "{key} = {value}",
        "config.key_header": "Key",
        "config.value_header": "Value",
        "config.source_header": "Source",
        "config.source_default": "default",
        "config.source_config": "config",
        "config.api_key_hidden": "***{last4}",
        "config.api_key_not_set": "Not set",
        "config.profiles_header": "Profiles:",
        "config.profile_current": "(current)",
        "config.no_profiles": "No profiles configured.",
        "config.create_profile_hint": "Create one: miru config profile create <name>",
        "config.profile_header": "Profile",
        "config.current_header": "Current",
        "config.settings_header": "Settings",
        "config.profile_name_required": "Profile name required.",
        "config.profile_not_found": "Profile '{name}' not found.",
        "config.available_profiles": "Available profiles: {profiles}",
        "config.profile_switched": "Switched to profile '{name}'",
        "config.profile_deleted": "Deleted profile '{name}'",
        "config.profile_exists": "Profile '{name}' already exists.",
        "config.profile_created": "Created profile '{name}'",
        "config.add_settings_hint": "Add settings: miru config profile set {name} default_host http://server:11434",
        "config.profile_set_hint": "Use: miru config set <key> <value> (profiles are auto-detected)",
        "config.edit_file_hint": "Or edit the config file directly",
        "config.invalid_action": "Invalid action: {action}",
        "config.valid_actions": "Valid actions: create, switch, delete, list",
        "config.config_dir": "Config directory: {path}",
        "config.config_file_path": "Config file: {path}",
        "config.reset_warning": "This will reset all configuration to defaults.",
        "config.use_force": "Use --force to confirm",
        "config.reset_success": "Configuration reset to defaults",
        
        # Tools command
        "tools.no_tools_found": "No tools found",
        "tools.available_tools": "Available Tools",
        "tools.name_header": "Name",
        "tools.description_header": "Description",
        "tools.parameters_header": "Parameters",
        "tools.total_tools": "Total: {count} tools",
        "tools.not_found": "Tool not found: {name}",
        "tools.list_available": "Use 'miru tools list' to see available tools",
        "tools.parameters": "Parameters:",
        "tools.ollama_format": "Ollama Format:",
        "tools.invalid_json": "Invalid JSON: {error}",
        "tools.invalid_arg_format": "Invalid argument format: {arg}",
        "tools.use_key_value": "Use KEY=VALUE format",
        "tools.validation_errors": "Validation errors:",
        "tools.executing": "Executing {name}...",
        "tools.result": "Result:",
        "tools.truncated": "(truncated)",
        "tools.exec_failed": "Execution failed: {error}",
        "tools.docs_written": "Documentation written to {path}",
        "tools.reference_header": "Tools Reference",
        "tools.overview_header": "Overview",
        "tools.total_tools_count": "Total tools: {count}",
        
        # Setup wizard
        "setup.title": "miru Setup Wizard",
        "setup.wizard_hint": "This wizard will help you configure miru CLI for first use.",
        "setup.continue": "Continue with setup?",
        "setup.cancelled": "Setup cancelled.",
        "setup.step1": "Step 1: Check Ollama Connection",
        "setup.ollama_running_version": "Ollama is running (version {version})",
        "setup.cannot_connect": "Cannot connect to Ollama at {host}",
        "setup.ensure_ollama": "Make sure Ollama is installed and running:",
        "setup.install_ollama": "1. Install Ollama: https://ollama.ai",
        "setup.start_ollama": "2. Start Ollama: ollama serve",
        "setup.try_again": "Try again?",
        "setup.waiting_ollama": "Waiting for Ollama...",
        "setup.still_not_accessible": "Ollama is still not accessible",
        "setup.run_setup_again": "Run 'miru setup' again after starting Ollama.",
        "setup.step2": "Step 2: Select Default Model",
        "setup.no_models": "No models found.",
        "setup.download_model": "Download a model with: miru pull <model>",
        "setup.popular_models": "Popular models:",
        "setup.gemma_desc": "gemma3:latest - Fast, efficient (4B)",
        "setup.qwen_desc": "qwen2.5:7b - Good balance (7B)",
        "setup.llama_desc": "llama3.2:latest - Large model (8B)",
        "setup.llava_desc": "llava:latest - Vision model",
        "setup.which_model": "Which model to download?",
        "setup.downloading": "Downloading {model}...",
        "setup.download_hint": "Run: miru pull {model}",
        "setup.available_models": "Available models ({count}):",
        "setup.and_more": "... and {count} more",
        "setup.using_first_model": "Using first model as default: {model}",
        "setup.select_default": "Select default model",
        "setup.model_not_found": "Model '{model}' not found locally.",
        "setup.use_anyway": "Use this model name anyway?",
        "setup.step3": "Step 3: Configure Settings",
        "setup.enable_history": "Enable prompt history?",
        "setup.max_entries": "Maximum history entries",
        "setup.enable_verbose": "Enable verbose mode by default?",
        "setup.create_alias": "Create an alias for quick access?",
        "setup.alias_name": "Alias name",
        "setup.model_to_alias": "Model to alias",
        "setup.alias_created": "Alias '{alias}' -> '{model}' created",
        "setup.step4": "Step 4: Verify Installation",
        "setup.config_file_label": "Configuration file:",
        "setup.default_model_label": "Default model:",
        "setup.host_label": "Host:",
        "setup.history_enabled_label": "History enabled:",
        "setup.next_steps": "Next steps:",
        "setup.try_chat": "Try: miru chat",
        "setup.try_run": "Try: miru run gemma3 'Hello'",
        "setup.see_commands": "See all commands: miru --help",
        
        # Quick command
        "quick.title": "Quick Commands",
        "quick.unknown_command": "Unknown quick command: {command}",
        "quick.available_commands": "Available commands: {commands}",
        "quick.missing_parameter": "Missing parameter: {param}",
        "quick.required_params": "Required parameters for '{command}': {params}",
        "quick.command_header": "Command",
        "quick.description_header": "Description",
        "quick.params_header": "Parameters",
        "quick.usage": "Usage: miru quick <command> <model> --param KEY=VALUE",
        "quick.example": "Example: miru quick code gemma3 --param language=python --param task='sort a list'",
        "quick.invalid_param": "Invalid parameter: {param}. Use KEY=VALUE",
        
        # Examples browser
        "examples.no_examples": "No examples found matching the criteria.",
        "examples.key_header": "Key",
        "examples.title_header": "Title",
        "examples.category_header": "Category",
        "examples.tags_header": "Tags",
        "examples.not_found": "Example '{name}' not found",
        "examples.use_list": "Use 'miru examples --list' to see available examples",
        "examples.desc_label": "Description:",
        "examples.category_label": "Category:",
        "examples.tags_label": "Tags:",
        "examples.command_label": "Command:",
        "examples.copied": "Command copied to clipboard",
        "examples.install_pyperclip": "Install 'pyperclip' to copy to clipboard: pip install pyperclip",
        "examples.command_shown": "Command is shown above",
        "examples.categories_title": "Categories",
        "examples.examples_count": "Examples",
        "examples.browser_title": "Usage Examples Browser",
        "examples.use_list_help": "Use --list to see all examples",
        "examples.use_category_help": "Use --category <name> to filter by category",
        "examples.use_tag_help": "Use --tag <tag> to filter by tag",
        "examples.use_name_help": "Use '<name>' to see example details",
        "examples.use_copy_help": "Use '<name> --copy' to copy command to clipboard",
        "examples.popular_examples": "Popular examples:",
        "examples.full_list": "Full list: miru examples --list",
        
        # Embed command
        "embed.model_label": "Model: {model}",
        "embed.dimensions_label": "Dimensions: {count}",
        "embed.duration_label": "Duration: {duration:.2f}ms",
        "embed.first_values": "Embedding (first 10 values):",
        "embed.more_values": "... ({count} more values)",
        "embed.file_not_found": "File not found: {path}",
        "embed.error_reading": "Error reading file: {error}",
        "embed.empty_file": "File is empty or has no valid lines",
        "embed.batch_model": "Model: {model}",
        "embed.batch_results": "results",
        "embed.invalid_batch_format": "--format jsonl is only for --batch. Use --format json for --file.",
        "embed.provide_input": "Provide text, file (--file), or batch (--batch).",
        "embed.input_examples": "Examples:\n"
                              '  miru embed nomic-embed-text "Hello world"\n'
                              "  miru embed nomic-embed-text --file document.txt\n"
                              "  miru embed nomic-embed-text --batch texts.txt",
        "embed.use_one_option": "Use only one option: text, --file, or --batch (do not combine).",
        
        # Batch command
        "batch.title": "Batch Results",
        "batch.col_status": "Status",
        "batch.col_time": "Time",
        "batch.summary": "Summary:",
        "batch.total": "Total:",
        "batch.success": "Success:",
        "batch.error": "Error:",
        "batch.tokens_generated": "Tokens generated:",
        "batch.total_time": "Total time:",
        "batch.avg_speed": "Average speed:",
        "batch.processing": "Processing {count} prompts with {model}",
        "batch.stop_on_error": "Stopping due to error (stop-on-error)",
        "batch.interrupted": "Interrupted by user",

        # History command
        "history.cleared": "History cleared",
        "history.none_found": "No history found",
        "history.title": "Prompt History",
        "history.index_header": "#",
        "history.datetime_header": "Date/Time",
        "history.command_header": "Command",
        "history.model_header": "Model",
        "history.prompt_header": "Prompt",
        "history.status_header": "Status",
        "history.use_show": "Use: miru history show <index> to see details",
        "history.entry_not_found": "Entry {index} not found",
        "history.datetime_label": "Date/Time:",
        "history.command_label": "Command:",
        "history.model_label": "Model:",
        "history.status_label": "Status:",
        "history.success": "Success",
        "history.failed": "Failed",
        "history.system_prompt_label": "System Prompt:",
        "history.prompt_label": "Prompt:",
        "history.response_label": "Response:",
        "history.metrics_label": "Metrics:",
        "history.tokens": "Tokens:",
        "history.speed": "Speed: {speed:.1f} tok/s",
        "history.time": "Time: {time:.1f}s",
        "history.error_label": "Error:",
        
        # Logs command
        "logs.none_found": "No logs found",
        "logs.files_title": "Log Files",
        "logs.file_header": "File",
        "logs.size_header": "Size",
        "logs.modified_header": "Modified",
        "logs.following": "Following... (Ctrl+C to stop)",
        "logs.stopped": "Stopped",
        "logs.delete_warning": "Delete all logs?",
        "logs.use_force": "Use --force to confirm",
        "logs.none_to_delete": "No logs to delete",
        "logs.deleted": "{count} log(s) deleted",
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
        "error.audio_processing": "Erro ao processar arquivo de áudio '{file}': {error}",
        "error.file_processing": "Erro ao processar arquivo '{path}': {error}",
        "error.system_prompt_file": "Erro ao ler arquivo de system prompt: {error}",
        "error.model_no_vision": "Modelo '{model}' não suporta imagens.",
        "error.available_models": "Modelos disponíveis:",
        "error.more_models": "... e mais {count}",

        "audio.transcription": "Transcrição de áudio",
        
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
        "chat.commands.recall": "Resgatar prompt anterior",
        "chat.commands.help_cmd": "Mostrar esta ajuda",

        "chat.session_ended": "Sessão encerrada · {turns} turno(s) · {model}",
        "chat.recall_title": "Prompts Anteriores",
        "chat.recall_empty": "Nenhum prompt anterior encontrado",
        "chat.recall_prompt": "Selecione o prompt (0-{count}) ou Enter para cancelar",
        "chat.recall_loaded": "Prompt carregado de {date}",
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
        
        # List table headers
        "list.size": "Tamanho",
        "list.modified": "Modificado",
        "list.expires": "Expira",
        
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
        
        # Status command
        "status.connection_failed": "Ollama não está respondendo em {host}",
        "status.check_running": "Verifique se o Ollama está rodando: ollama serve",
        "status.accessible": "Ollama está acessível em {host}",
        "status.property": "Propriedade",
        "status.value": "Valor",
        "status.online": "Online",
        "status.loaded_vram_count": "Modelos carregados na VRAM ({count}):",
        "status.no_models_vram": "Nenhum modelo carregado na VRAM",
        "status.connection_error": "Não é possível conectar ao Ollama em {host}",
        "status.timeout_error": "Timeout ao conectar ao Ollama em {host}",
        "status.error_unexpected": "Erro: {error}",
        "status.model_unloaded": "Modelo {model} descarregado",
        "status.stop_error": "Erro ao parar modelo: {error}",
        "status.no_models_found": "Nenhum modelo encontrado para '{query}'",
        "status.models_matching": "Modelos correspondentes a '{query}'",
        
        # Config command
        "config.unknown_key": "Chave de configuração desconhecida: {key}",
        "config.valid_keys": "Chaves válidas: default_host, default_model, default_timeout,",
        "config.valid_keys_more": "  default_temperature, default_max_tokens, default_top_p,",
        "config.valid_keys_more2": "  default_top_k, default_seed, history_enabled,",
        "config.valid_keys_more3": "  history_max_entries, verbose, tavily_api_key,",
        "config.valid_keys_more4": "  enable_tools, enable_tavily, tool_mode, sandbox_dir",
        "config.invalid_boolean": "Valor booleano inválido: {value}",
        "config.valid_boolean": "Valores válidos: true, false, 1, 0, yes, no",
        "config.invalid_tool_mode": "tool_mode inválido: {value}",
        "config.valid_tool_modes": "Valores válidos: manual, auto, auto_safe",
        "config.invalid_float": "Valor float inválido: {value}",
        "config.invalid_integer": "Valor inteiro inválido: {value}",
        "config.api_key_format_warning": "Aviso: API key não corresponde ao formato esperado (tvly-...)",
        "config.key_set": "Definido {key} = {value}",
        "config.config_file": "Arquivo de config: {path}",
        "config.key_value": "{key} = {value}",
        "config.key_header": "Chave",
        "config.value_header": "Valor",
        "config.source_header": "Origem",
        "config.source_default": "default",
        "config.source_config": "config",
        "config.api_key_hidden": "***{last4}",
        "config.api_key_not_set": "Não definido",
        "config.profiles_header": "Profiles:",
        "config.profile_current": "(atual)",
        "config.no_profiles": "Nenhum profile configurado.",
        "config.create_profile_hint": "Crie um: miru config profile create <nome>",
        "config.profile_header": "Profile",
        "config.current_header": "Atual",
        "config.settings_header": "Configurações",
        "config.profile_name_required": "Nome do profile é obrigatório.",
        "config.profile_not_found": "Profile '{name}' não encontrado.",
        "config.available_profiles": "Profiles disponíveis: {profiles}",
        "config.profile_switched": "Mudado para profile '{name}'",
        "config.profile_deleted": "Profile '{name}' deletado",
        "config.profile_exists": "Profile '{name}' já existe.",
        "config.profile_created": "Profile '{name}' criado",
        "config.add_settings_hint": "Adicione configurações: miru config profile set {name} default_host http://server:11434",
        "config.profile_set_hint": "Use: miru config set <chave> <valor> (profiles são auto-detectados)",
        "config.edit_file_hint": "Ou edite o arquivo de config diretamente",
        "config.invalid_action": "Ação inválida: {action}",
        "config.valid_actions": "Ações válidas: create, switch, delete, list",
        "config.config_dir": "Diretório de config: {path}",
        "config.config_file_path": "Arquivo de config: {path}",
        "config.reset_warning": "Isto irá resetar toda a configuração para os valores padrão.",
        "config.use_force": "Use --force para confirmar",
        "config.reset_success": "Configuração resetada para os valores padrão",
        
        # Tools command
        "tools.no_tools_found": "Nenhuma ferramenta encontrada",
        "tools.available_tools": "Ferramentas Disponíveis",
        "tools.name_header": "Nome",
        "tools.description_header": "Descrição",
        "tools.parameters_header": "Parâmetros",
        "tools.total_tools": "Total: {count} ferramentas",
        "tools.not_found": "Ferramenta não encontrada: {name}",
        "tools.list_available": "Use 'miru tools list' para ver ferramentas disponíveis",
        "tools.parameters": "Parâmetros:",
        "tools.ollama_format": "Formato Ollama:",
        "tools.invalid_json": "JSON inválido: {error}",
        "tools.invalid_arg_format": "Formato de argumento inválido: {arg}",
        "tools.use_key_value": "Use formato CHAVE=VALOR",
        "tools.validation_errors": "Erros de validação:",
        "tools.executing": "Executando {name}...",
        "tools.result": "Resultado:",
        "tools.truncated": "(truncado)",
        "tools.exec_failed": "Falha na execução: {error}",
        "tools.docs_written": "Documentação escrita em {path}",
        "tools.reference_header": "Referência de Ferramentas",
        "tools.overview_header": "Visão Geral",
        "tools.total_tools_count": "Total de ferramentas: {count}",
        
        # Setup wizard
        "setup.title": "Assistente de Configuração do miru",
        "setup.wizard_hint": "Este assistente irá ajudá-lo a configurar o miru CLI para primeiro uso.",
        "setup.continue": "Continuar com a configuração?",
        "setup.cancelled": "Configuração cancelada.",
        "setup.step1": "Passo 1: Verificar Conexão com Ollama",
        "setup.ollama_running_version": "Ollama está rodando (versão {version})",
        "setup.cannot_connect": "Não é possível conectar ao Ollama em {host}",
        "setup.ensure_ollama": "Certifique-se de que o Ollama está instalado e rodando:",
        "setup.install_ollama": "1. Instale o Ollama: https://ollama.ai",
        "setup.start_ollama": "2. Inicie o Ollama: ollama serve",
        "setup.try_again": "Tentar novamente?",
        "setup.waiting_ollama": "Aguardando Ollama...",
        "setup.still_not_accessible": "Ollama ainda não está acessível",
        "setup.run_setup_again": "Execute 'miru setup' novamente após iniciar o Ollama.",
        "setup.step2": "Passo 2: Selecionar Modelo Padrão",
        "setup.no_models": "Nenhum modelo encontrado.",
        "setup.download_model": "Baixe um modelo com: miru pull <modelo>",
        "setup.popular_models": "Modelos populares:",
        "setup.gemma_desc": "gemma3:latest - Rápido, eficiente (4B)",
        "setup.qwen_desc": "qwen2.5:7b - Bom equilíbrio (7B)",
        "setup.llama_desc": "llama3.2:latest - Modelo grande (8B)",
        "setup.llava_desc": "llava:latest - Modelo de visão",
        "setup.which_model": "Qual modelo baixar?",
        "setup.downloading": "Baixando {model}...",
        "setup.download_hint": "Execute: miru pull {model}",
        "setup.available_models": "Modelos disponíveis ({count}):",
        "setup.and_more": "... e mais {count}",
        "setup.using_first_model": "Usando primeiro modelo como padrão: {model}",
        "setup.select_default": "Selecione modelo padrão",
        "setup.model_not_found": "Modelo '{model}' não encontrado localmente.",
        "setup.use_anyway": "Usar este nome de modelo mesmo assim?",
        "setup.step3": "Passo 3: Configurar Definições",
        "setup.enable_history": "Habilitar histórico de prompts?",
        "setup.max_entries": "Máximo de entradas no histórico",
        "setup.enable_verbose": "Habilitar modo verbose por padrão?",
        "setup.create_alias": "Criar um alias para acesso rápido?",
        "setup.alias_name": "Nome do alias",
        "setup.model_to_alias": "Modelo para alias",
        "setup.alias_created": "Alias '{alias}' -> '{model}' criado",
        "setup.step4": "Passo 4: Verificar Instalação",
        "setup.config_file_label": "Arquivo de configuração:",
        "setup.default_model_label": "Modelo padrão:",
        "setup.host_label": "Host:",
        "setup.history_enabled_label": "Histórico habilitado:",
        "setup.next_steps": "Próximos passos:",
        "setup.try_chat": "Experimente: miru chat",
        "setup.try_run": "Experimente: miru run gemma3 'Olá'",
        "setup.see_commands": "Veja todos os comandos: miru --help",
        
        # Quick command
        "quick.title": "Comandos Rápidos",
        "quick.unknown_command": "Comando rápido desconhecido: {command}",
        "quick.available_commands": "Comandos disponíveis: {commands}",
        "quick.missing_parameter": "Parâmetro faltando: {param}",
        "quick.required_params": "Parâmetros obrigatórios para '{command}': {params}",
        "quick.command_header": "Comando",
        "quick.description_header": "Descrição",
        "quick.params_header": "Parâmetros",
        "quick.usage": "Uso: miru quick <comando> <modelo> --param CHAVE=VALOR",
        "quick.example": "Exemplo: miru quick code gemma3 --param language=python --param task='ordenar lista'",
        "quick.invalid_param": "Parâmetro inválido: {param}. Use CHAVE=VALOR",
        
        # Examples browser
        "examples.no_examples": "Nenhum exemplo encontrado com os critérios.",
        "examples.key_header": "Chave",
        "examples.title_header": "Título",
        "examples.category_header": "Categoria",
        "examples.tags_header": "Tags",
        "examples.not_found": "Exemplo '{name}' não encontrado",
        "examples.use_list": "Use 'miru examples --list' para ver exemplos disponíveis",
        "examples.desc_label": "Descrição:",
        "examples.category_label": "Categoria:",
        "examples.tags_label": "Tags:",
        "examples.command_label": "Comando:",
        "examples.copied": "Comando copiado para a área de transferência",
        "examples.install_pyperclip": "Instale 'pyperclip' para copiar: pip install pyperclip",
        "examples.command_shown": "Comando mostrado acima",
        "examples.categories_title": "Categorias",
        "examples.examples_count": "Exemplos",
        "examples.browser_title": "Navegador de Exemplos de Uso",
        "examples.use_list_help": "Use --list para ver todos os exemplos",
        "examples.use_category_help": "Use --category <nome> para filtrar por categoria",
        "examples.use_tag_help": "Use --tag <tag> para filtrar por tag",
        "examples.use_name_help": "Use '<nome>' para ver detalhes do exemplo",
        "examples.use_copy_help": "Use '<nome> --copy' para copiar comando",
        "examples.popular_examples": "Exemplos populares:",
        "examples.full_list": "Lista completa: miru examples --list",
        
        # Embed command
        "embed.model_label": "Modelo: {model}",
        "embed.dimensions_label": "Dimensões: {count}",
        "embed.duration_label": "Duração: {duration:.2f}ms",
        "embed.first_values": "Embedding (primeiros 10 valores):",
        "embed.more_values": "... ({count} valores a mais)",
        "embed.file_not_found": "Arquivo não encontrado: {path}",
        "embed.error_reading": "Erro ao ler arquivo: {error}",
        "embed.empty_file": "Arquivo vazio ou sem linhas válidas",
        "embed.batch_model": "Modelo: {model}",
        "embed.batch_results": "resultados",
        "embed.invalid_batch_format": "--format jsonl é apenas para --batch. Use --format json para --file.",
        "embed.provide_input": "Forneça texto, arquivo (--file), ou batch (--batch).",
        "embed.input_examples": "Exemplos:\n"
                              '  miru embed nomic-embed-text "Olá mundo"\n'
                              "  miru embed nomic-embed-text --file documento.txt\n"
                              "  miru embed nomic-embed-text --batch textos.txt",
        "embed.use_one_option": "Use apenas uma opção: texto, --file, ou --batch (não combine).",
        
        # Batch command
        "batch.title": "Resultados do Batch",
        "batch.col_status": "Status",
        "batch.col_time": "Tempo",
        "batch.summary": "Resumo:",
        "batch.total": "Total:",
        "batch.success": "Sucesso:",
        "batch.error": "Erro:",
        "batch.tokens_generated": "Tokens gerados:",
        "batch.total_time": "Tempo total:",
        "batch.avg_speed": "Velocidade média:",
        "batch.processing": "Processando {count} prompts com {model}",
        "batch.stop_on_error": "Parando devido a erro (stop-on-error)",
        "batch.interrupted": "Interrompido pelo usuário",

        # History command
        "history.cleared": "Histórico limpo",
        "history.none_found": "Nenhum histórico encontrado",
        "history.title": "Histórico de Prompts",
        "history.index_header": "#",
        "history.datetime_header": "Data/Hora",
        "history.command_header": "Comando",
        "history.model_header": "Modelo",
        "history.prompt_header": "Prompt",
        "history.status_header": "Status",
        "history.use_show": "Use: miru history show <índice> para ver detalhes",
        "history.entry_not_found": "Entrada {index} não encontrada",
        "history.datetime_label": "Data/Hora:",
        "history.command_label": "Comando:",
        "history.model_label": "Modelo:",
        "history.status_label": "Status:",
        "history.success": "Sucesso",
        "history.failed": "Falhou",
        "history.system_prompt_label": "System Prompt:",
        "history.prompt_label": "Prompt:",
        "history.response_label": "Resposta:",
        "history.metrics_label": "Métricas:",
        "history.tokens": "Tokens:",
        "history.speed": "Velocidade: {speed:.1f} tok/s",
        "history.time": "Tempo: {time:.1f}s",
        "history.error_label": "Erro:",
        
        # Logs command
        "logs.none_found": "Nenhum log encontrado",
        "logs.files_title": "Arquivos de Log",
        "logs.file_header": "Arquivo",
        "logs.size_header": "Tamanho",
        "logs.modified_header": "Modificado",
        "logs.following": "Seguindo... (Ctrl+C para parar)",
        "logs.stopped": "Parado",
        "logs.delete_warning": "Deletar todos os logs?",
        "logs.use_force": "Use --force para confirmar",
        "logs.none_to_delete": "Nenhum log para deletar",
        "logs.deleted": "{count} log(s) deletado(s)",
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
        "error.audio_processing": "Error al procesar archivo de audio '{file}': {error}",
        "error.file_processing": "Error al procesar archivo '{path}': {error}",
        "error.system_prompt_file": "Error al leer archivo de system prompt: {error}",
        "error.model_no_vision": "Modelo '{model}' no soporta imágenes.",
        "error.available_models": "Modelos disponibles:",
        "error.more_models": "... y {count} más",

        "audio.transcription": "Transcripción de audio",
        
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
        "chat.commands.recall": "Recuperar prompt anterior",
        "chat.commands.help_cmd": "Mostrar esta ayuda",

        "chat.session_ended": "Sesión terminada · {turns} turno(s) · {model}",
        "chat.recall_title": "Prompts Anteriores",
        "chat.recall_empty": "Ningún prompt anterior encontrado",
        "chat.recall_prompt": "Seleccione el prompt (0-{count}) o Enter para cancelar",
        "chat.recall_loaded": "Prompt cargado de {date}",
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
        
        # List table headers
        "list.size": "Tamaño",
        "list.modified": "Modificado",
        "list.expires": "Expira",
        
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
        
        # Status command
        "status.connection_failed": "Ollama no está respondiendo en {host}",
        "status.check_running": "Verifique que Ollama esté ejecutándose: ollama serve",
        "status.accessible": "Ollama está accesible en {host}",
        "status.property": "Propiedad",
        "status.value": "Valor",
        "status.online": "En línea",
        "status.loaded_vram_count": "Modelos cargados en VRAM ({count}):",
        "status.no_models_vram": "Ningún modelo cargado en VRAM",
        "status.connection_error": "No se puede conectar a Ollama en {host}",
        "status.timeout_error": "Tiempo de espera agotado conectando a Ollama en {host}",
        "status.error_unexpected": "Error: {error}",
        "status.model_unloaded": "Modelo {model} descargado",
        "status.stop_error": "Error al detener modelo: {error}",
        "status.no_models_found": "Ningún modelo encontrado para '{query}'",
        "status.models_matching": "Modelos que coinciden con '{query}'",
        
        # Config command
        "config.unknown_key": "Clave de configuración desconocida: {key}",
        "config.valid_keys": "Claves válidas: default_host, default_model, default_timeout,",
        "config.valid_keys_more": "  default_temperature, default_max_tokens, default_top_p,",
        "config.valid_keys_more2": "  default_top_k, default_seed, history_enabled,",
        "config.valid_keys_more3": "  history_max_entries, verbose, tavily_api_key,",
        "config.valid_keys_more4": "  enable_tools, enable_tavily, tool_mode, sandbox_dir",
        "config.invalid_boolean": "Valor booleano inválido: {value}",
        "config.valid_boolean": "Valores válidos: true, false, 1, 0, yes, no",
        "config.invalid_tool_mode": "tool_mode inválido: {value}",
        "config.valid_tool_modes": "Valores válidos: manual, auto, auto_safe",
        "config.invalid_float": "Valor float inválido: {value}",
        "config.invalid_integer": "Valor entero inválido: {value}",
        "config.api_key_format_warning": "Advertencia: API key no coincide con el formato esperado (tvly-...)",
        "config.key_set": "Establecido {key} = {value}",
        "config.config_file": "Archivo de config: {path}",
        "config.key_value": "{key} = {value}",
        "config.key_header": "Clave",
        "config.value_header": "Valor",
        "config.source_header": "Origen",
        "config.source_default": "por defecto",
        "config.source_config": "config",
        "config.api_key_hidden": "***{last4}",
        "config.api_key_not_set": "No establecido",
        "config.profiles_header": "Profiles:",
        "config.profile_current": "(actual)",
        "config.no_profiles": "Ningún profile configurado.",
        "config.create_profile_hint": "Cree uno: miru config profile create <nombre>",
        "config.profile_header": "Profile",
        "config.current_header": "Actual",
        "config.settings_header": "Configuraciones",
        "config.profile_name_required": "Nombre de profile requerido.",
        "config.profile_not_found": "Profile '{name}' no encontrado.",
        "config.available_profiles": "Profiles disponibles: {profiles}",
        "config.profile_switched": "Cambiado a profile '{name}'",
        "config.profile_deleted": "Profile '{name}' eliminado",
        "config.profile_exists": "Profile '{name}' ya existe.",
        "config.profile_created": "Profile '{name}' creado",
        "config.add_settings_hint": "Agregue configuraciones: miru config profile set {name} default_host http://server:11434",
        "config.profile_set_hint": "Use: miru config set <clave> <valor> (profiles son auto-detectados)",
        "config.edit_file_hint": "O edite el archivo de config directamente",
        "config.invalid_action": "Acción inválida: {action}",
        "config.valid_actions": "Acciones válidas: create, switch, delete, list",
        "config.config_dir": "Directorio de config: {path}",
        "config.config_file_path": "Archivo de config: {path}",
        "config.reset_warning": "Esto reseteará toda la configuración a valores por defecto.",
        "config.use_force": "Use --force para confirmar",
        "config.reset_success": "Configuración reseteada a valores por defecto",
        
        # Tools command
        "tools.no_tools_found": "Ninguna herramienta encontrada",
        "tools.available_tools": "Herramientas Disponibles",
        "tools.name_header": "Nombre",
        "tools.description_header": "Descripción",
        "tools.parameters_header": "Parámetros",
        "tools.total_tools": "Total: {count} herramientas",
        "tools.not_found": "Herramienta no encontrada: {name}",
        "tools.list_available": "Use 'miru tools list' para ver herramientas disponibles",
        "tools.parameters": "Parámetros:",
        "tools.ollama_format": "Formato Ollama:",
        "tools.invalid_json": "JSON inválido: {error}",
        "tools.invalid_arg_format": "Formato de argumento inválido: {arg}",
        "tools.use_key_value": "Use formato CLAVE=VALOR",
        "tools.validation_errors": "Errores de validación:",
        "tools.executing": "Ejecutando {name}...",
        "tools.result": "Resultado:",
        "tools.truncated": "(truncado)",
        "tools.exec_failed": "Ejecución fallida: {error}",
        "tools.docs_written": "Documentación escrita en {path}",
        "tools.reference_header": "Referencia de Herramientas",
        "tools.overview_header": "Vista General",
        "tools.total_tools_count": "Total de herramientas: {count}",
        
        # Setup wizard
        "setup.title": "Asistente de Configuración de miru",
        "setup.wizard_hint": "Este asistente le ayudará a configurar miru CLI para primer uso.",
        "setup.continue": "¿Continuar con la configuración?",
        "setup.cancelled": "Configuración cancelada.",
        "setup.step1": "Paso 1: Verificar Conexión con Ollama",
        "setup.ollama_running_version": "Ollama está ejecutándose (versión {version})",
        "setup.cannot_connect": "No se puede conectar a Ollama en {host}",
        "setup.ensure_ollama": "Asegúrese de que Ollama esté instalado y ejecutándose:",
        "setup.install_ollama": "1. Instale Ollama: https://ollama.ai",
        "setup.start_ollama": "2. Inicie Ollama: ollama serve",
        "setup.try_again": "¿Intentar de nuevo?",
        "setup.waiting_ollama": "Esperando Ollama...",
        "setup.still_not_accessible": "Ollama todavía no está accesible",
        "setup.run_setup_again": "Ejecute 'miru setup' nuevamente después de iniciar Ollama.",
        "setup.step2": "Paso 2: Seleccionar Modelo Por Defecto",
        "setup.no_models": "Ningún modelo encontrado.",
        "setup.download_model": "Descargue un modelo con: miru pull <modelo>",
        "setup.popular_models": "Modelos populares:",
        "setup.gemma_desc": "gemma3:latest - Rápido, eficiente (4B)",
        "setup.qwen_desc": "qwen2.5:7b - Buen equilibrio (7B)",
        "setup.llama_desc": "llama3.2:latest - Modelo grande (8B)",
        "setup.llava_desc": "llava:latest - Modelo de visión",
        "setup.which_model": "¿Qué modelo descargar?",
        "setup.downloading": "Descargando {model}...",
        "setup.download_hint": "Ejecute: miru pull {model}",
        "setup.available_models": "Modelos disponibles ({count}):",
        "setup.and_more": "... y {count} más",
        "setup.using_first_model": "Usando primer modelo como por defecto: {model}",
        "setup.select_default": "Seleccione modelo por defecto",
        "setup.model_not_found": "Modelo '{model}' no encontrado localmente.",
        "setup.use_anyway": "¿Usar este nombre de modelo de todas formas?",
        "setup.step3": "Paso 3: Configurar Ajustes",
        "setup.enable_history": "¿Habilitar historial de prompts?",
        "setup.max_entries": "Máximo de entradas en historial",
        "setup.enable_verbose": "¿Habilitar modo verbose por defecto?",
        "setup.create_alias": "¿Crear un alias para acceso rápido?",
        "setup.alias_name": "Nombre del alias",
        "setup.model_to_alias": "Modelo para alias",
        "setup.alias_created": "Alias '{alias}' -> '{model}' creado",
        "setup.step4": "Paso 4: Verificar Instalación",
        "setup.config_file_label": "Archivo de configuración:",
        "setup.default_model_label": "Modelo por defecto:",
        "setup.host_label": "Host:",
        "setup.history_enabled_label": "Historial habilitado:",
        "setup.next_steps": "Próximos pasos:",
        "setup.try_chat": "Pruebe: miru chat",
        "setup.try_run": "Pruebe: miru run gemma3 'Hola'",
        "setup.see_commands": "Vea todos los comandos: miru --help",
        
        # Quick command
        "quick.title": "Comandos Rápidos",
        "quick.unknown_command": "Comando rápido desconocido: {command}",
        "quick.available_commands": "Comandos disponibles: {commands}",
        "quick.missing_parameter": "Parámetro faltante: {param}",
        "quick.required_params": "Parámetros requeridos para '{command}': {params}",
        "quick.command_header": "Comando",
        "quick.description_header": "Descripción",
        "quick.params_header": "Parámetros",
        "quick.usage": "Uso: miru quick <comando> <modelo> --param CLAVE=VALOR",
        "quick.example": "Ejemplo: miru quick code gemma3 --param language=python --param task='ordenar lista'",
        "quick.invalid_param": "Parámetro inválido: {param}. Use CLAVE=VALOR",
        
        # Examples browser
        "examples.no_examples": "Ningún ejemplo encontrado con los criterios.",
        "examples.key_header": "Clave",
        "examples.title_header": "Título",
        "examples.category_header": "Categoría",
        "examples.tags_header": "Tags",
        "examples.not_found": "Ejemplo '{name}' no encontrado",
        "examples.use_list": "Use 'miru examples --list' para ver ejemplos disponibles",
        "examples.desc_label": "Descripción:",
        "examples.category_label": "Categoría:",
        "examples.tags_label": "Tags:",
        "examples.command_label": "Comando:",
        "examples.copied": "Comando copiado al portapapeles",
        "examples.install_pyperclip": "Instale 'pyperclip' para copiar: pip install pyperclip",
        "examples.command_shown": "Comando mostrado arriba",
        "examples.categories_title": "Categorías",
        "examples.examples_count": "Ejemplos",
        "examples.browser_title": "Navegador de Ejemplos de Uso",
        "examples.use_list_help": "Use --list para ver todos los ejemplos",
        "examples.use_category_help": "Use --category <nombre> para filtrar por categoría",
        "examples.use_tag_help": "Use --tag <tag> para filtrar por tag",
        "examples.use_name_help": "Use '<nombre>' para ver detalles del ejemplo",
        "examples.use_copy_help": "Use '<nombre> --copy' para copiar comando",
        "examples.popular_examples": "Ejemplos populares:",
        "examples.full_list": "Lista completa: miru examples --list",
        
        # Embed command
        "embed.model_label": "Modelo: {model}",
        "embed.dimensions_label": "Dimensiones: {count}",
        "embed.duration_label": "Duración: {duration:.2f}ms",
        "embed.first_values": "Embedding (primeros 10 valores):",
        "embed.more_values": "... ({count} valores más)",
        "embed.file_not_found": "Archivo no encontrado: {path}",
        "embed.error_reading": "Error al leer archivo: {error}",
        "embed.empty_file": "Archivo vacío o sin líneas válidas",
        "embed.batch_model": "Modelo: {model}",
        "embed.batch_results": "resultados",
        "embed.invalid_batch_format": "--format jsonl es solo para --batch. Use --format json para --file.",
        "embed.provide_input": "Proporcione texto, archivo (--file), o batch (--batch).",
        "embed.input_examples": "Ejemplos:\n"
                              '  miru embed nomic-embed-text "Hola mundo"\n'
                              "  miru embed nomic-embed-text --file documento.txt\n"
                              "  miru embed nomic-embed-text --batch textos.txt",
        "embed.use_one_option": "Use solo una opción: texto, --file, o --batch (no combine).",
        
        # Batch command
        "batch.title": "Resultados del Batch",
        "batch.col_status": "Estado",
        "batch.col_time": "Tiempo",
        "batch.summary": "Resumen:",
        "batch.total": "Total:",
        "batch.success": "Éxito:",
        "batch.error": "Error:",
        "batch.tokens_generated": "Tokens generados:",
        "batch.total_time": "Tiempo total:",
        "batch.avg_speed": "Velocidad media:",
        "batch.processing": "Procesando {count} prompts con {model}",
        "batch.stop_on_error": "Deteniendo debido a error (stop-on-error)",
        "batch.interrupted": "Interrumpido por el usuario",

        # History command
        "history.cleared": "Historial limpiado",
        "history.none_found": "Ningún historial encontrado",
        "history.title": "Historial de Prompts",
        "history.index_header": "#",
        "history.datetime_header": "Fecha/Hora",
        "history.command_header": "Comando",
        "history.model_header": "Modelo",
        "history.prompt_header": "Prompt",
        "history.status_header": "Estado",
        "history.use_show": "Use: miru history show <índice> para ver detalles",
        "history.entry_not_found": "Entrada {index} no encontrada",
        "history.datetime_label": "Fecha/Hora:",
        "history.command_label": "Comando:",
        "history.model_label": "Modelo:",
        "history.status_label": "Estado:",
        "history.success": "Éxito",
        "history.failed": "Falló",
        "history.system_prompt_label": "System Prompt:",
        "history.prompt_label": "Prompt:",
        "history.response_label": "Respuesta:",
        "history.metrics_label": "Métricas:",
        "history.tokens": "Tokens:",
        "history.speed": "Velocidad: {speed:.1f} tok/s",
        "history.time": "Tiempo: {time:.1f}s",
        "history.error_label": "Error:",
        
        # Logs command
        "logs.none_found": "Ningún log encontrado",
        "logs.files_title": "Archivos de Log",
        "logs.file_header": "Archivo",
        "logs.size_header": "Tamaño",
        "logs.modified_header": "Modificado",
        "logs.following": "Siguiendo... (Ctrl+C para detener)",
        "logs.stopped": "Detenido",
        "logs.delete_warning": "¿Eliminar todos los logs?",
        "logs.use_force": "Use --force para confirmar",
        "logs.none_to_delete": "Ningún log para eliminar",
        "logs.deleted": "{count} log(s) eliminado(s)",
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


def t(msg_key: str, **kwargs: Any) -> str:
    """Translate a message key to the current language.
    
    Args:
        msg_key: Message key (e.g., "error.model_not_found")
        **kwargs: Format variables for the message
        
    Returns:
        Translated and formatted message
        
    Example:
        >>> set_language("pt_BR")
        >>> t("error.model_not_found", model="gemma3:latest")
        "Modelo 'gemma3:latest' não encontrado."
    """
    messages = MESSAGES.get(_current_language, MESSAGES[DEFAULT_LANGUAGE])
    message = messages.get(msg_key, MESSAGES[DEFAULT_LANGUAGE].get(msg_key, msg_key))
    
    try:
        return message.format(**kwargs)
    except KeyError:
        return message


def init_i18n() -> None:
    """Initialize i18n system with detected language."""
    global _current_language
    _current_language = detect_language()