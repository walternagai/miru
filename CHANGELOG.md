# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-04-07

### Added

#### Internationalization (i18n)
- **New i18n system** with support for Portuguese (Brazil), English, and Spanish
- Auto-detection of system language via `LANG` environment variable
- Manual language override via `MIRU_LANG` environment variable
- Comprehensive message catalog with 80+ translatable strings
- Categories: errors, success, suggestions, chat, tools, config, setup, status

#### Core Module (`miru/core/`)
- **Unified configuration** in single `config.py` file
  - Cached configuration for performance
  - Clear precedence chain: CLI > Env > Config > Default
  - Language preference in config
- **Custom exception hierarchy** in `errors.py`
  - `MiruError` base class
  - `ModelNotFoundError` with suggestions
  - `ConnectionError` with helpful hints
  - `ValidationError`, `ToolExecutionError`, `ConfigError`, `FileProcessingError`
- **i18n module** (`core/i18n.py`)
  - `t()` function for translations
  - `set_language()`, `get_language()`, `detect_language()` functions
  - `init_i18n()` auto-initialization

#### UI Module (`miru/ui/`)
- **Separation of concerns** - UI logic isolated from business logic
- **`render.py`** - Consistent output formatting
  - `render_error()`, `render_success()`, `render_warning()`, `render_info()`
  - `render_model_table()`, `render_metrics()`, `render_code()`, `render_table()`
  - Full i18n support
- **`progress.py`** - Progress reporting utilities
  - `ProgressReporter` class for determinate/indeterminate progress
  - Context manager `track_progress()`
  - Rich-based progress bars with spinners
- **`prompts.py`** - Interactive user inputs
  - `confirm()`, `prompt_input()`, `prompt_choice()`, `prompt_multiselect()`
  - Rich-based prompts with i18n support

#### CLI Improvements
- **Standardized short flags** across all commands
  - `--host` / `-h` - Server URL
  - `--format` / `-f` - Output format
  - `--quiet` / `-q` - Minimal output
  - `--system` / `-s` - System prompt
  - `--image` / `-i` - Image file
  - `--file` / `-f` - Input file
  - `--temperature` / `-t` - Sampling temperature
  - `--max-tokens` / `-m` - Max tokens
  - `--top-p` / `-p` - Nucleus sampling
  - `--top-k` / `-k` - Top-k sampling
  - `--ctx` / `-c` - Context window

### Changed

#### Refactored
- **`miru/commands/chat.py`** - Complete refactor with i18n and new modules
- **`miru/config_manager.py`** - Now a compatibility wrapper around `core/config.py`
- **`miru/__init__.py`** - Initializes i18n on import

#### Improved
- **Error messages** now include contextual suggestions
- **Configuration loading** is cached for better performance
- **Code organization** with clear separation of concerns

### Fixed
- **Compatibility** - Backward compatible with existing code
- **Import structure** - All legacy imports still work via wrappers

### Documentation
- **New `docs/REFACTORING.md`** - Complete guide for refactored modules
- **Updated README.md** - Added i18n section and examples
- **Code examples** - Updated with short flags

---

## [0.3.0] - 2026-04-06

### Added

#### Tools / Function Calling
- **Complete tool system** for Ollama function calling
- **File tools** with sandbox security
  - `read_file`, `write_file`, `edit_file`, `delete_file`
  - `list_files`, `search_files`, `file_exists`, `get_file_info`
- **System tools** with whitelist security
  - `run_command` (dangerous, requires approval)
  - `get_env` (whitelisted variables only)
  - `get_current_dir`
- **Tavily web search integration**
  - `tavily_search` - Web search with results
  - `tavily_search_images` - Image search
  - `tavily_extract` - URL content extraction
  - Query variation generation for better results
- **Tool execution modes**
  - `DISABLED` - No tools
  - `MANUAL` - Approve every tool
  - `AUTO` - Execute all automatically
  - `AUTO_SAFE` - Auto for safe tools, approve dangerous (default)
- **Sandbox system** for file operations
  - Path traversal prevention
  - Extension whitelisting
  - Permission flags (read/write/delete)
- **Approval flow** for dangerous operations

#### Security
- **FileSandbox** - Isolates file operations to specific directory
- **CommandWhitelist** - Only explicitly allowed commands
- **EnvironmentWhitelist** - Only whitelisted env vars readable
- **Tool classification** - Safe vs Dangerous tools

#### Integration
- **`--enable-tools`** flag for `chat` and `run` commands
- **`--enable-tavily`** flag for web search
- **`--sandbox-dir`** for file operations sandbox
- **`--tool-mode`** for execution mode selection
- **Config options** for persistent tool settings
  - `enable_tools`, `enable_tavily`, `tool_mode`, `sandbox_dir`

### Changed
- **`miru run`** and **`miru chat`** now support tools
- **Tool integration** in `miru/tool_integration.py`
- **Enhanced tool loop** with progress indicators

---

## [0.2.0] - 2026-03-15

### Added

#### Session Management
- **Save/restore chat sessions** with `miru session`
- **Export sessions** to JSON, Markdown, TXT
- **Session persistence** in `~/.miru/sessions/`

#### Batch Processing
- **`miru batch`** command for processing multiple prompts
- **JSONL input format** with metadata
- **Stop-on-error option**

#### Model Comparison
- **`miru compare`** for side-by-side model benchmarking
- **Reproducible results** with seed option
- **Metrics output** in JSON format

### Changed
- **Improved streaming** with markdown rendering
- **Better error handling** with suggestions

---

## [0.1.0] - 2026-02-01

### Added

#### Core Features
- **Interactive chat** with multi-turn support
- **Single prompt execution** with `miru run`
- **Model management** - pull, delete, copy, list models
- **Multimodal support** - images, files, audio

#### Configuration
- **Persistent config** in `~/.miru/config.toml`
- **Model aliases** for common shortcuts
- **Prompt templates** with parameter substitution

#### History
- **Prompt history** in `~/.miru/history.jsonl`
- **Search and filter** capabilities

#### Quick Commands
- **Pre-defined commands** for common tasks
- **Code generation, review, refactoring**
- **Translation, summarization, explanation**

#### Examples
- **Example browser** with `miru examples`
- **Categories and tags**
- **Copy to clipboard**

#### Shell Completion
- **Bash, Zsh, Fish** completion scripts
- **Auto-generated** via `miru completion`

### Infrastructure
- **Async HTTP client** with httpx
- **Rich terminal UI** for formatting
- **Typer CLI framework**

---

## [0.0.1] - 2026-01-15

### Added
- Initial release
- Basic Ollama CLI functionality
- Chat and run commands
- Model listing