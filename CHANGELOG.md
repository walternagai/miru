# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-04-07

### Added

#### Chat Command Enhancements

- **`/recall` command** - Recall previous prompts from history
  - `/recall` - Interactive list of last 10 prompts
  - `/recall <n>` - Direct recall by index
  - Preserves context (model, system_prompt) in current session
  - Full i18n support (en_US, pt_BR, es_ES)
  - Example usage:
    ```bash
    >>> /recall           # Shows interactive list
    >>> /recall 3         # Loads prompt #3 directly
    ```

- **Markdown rendering** in history display
  - `miru history show <index>` now renders responses with Rich Markdown
  - Headers, bold, italic, code blocks, tables properly formatted
  - Same visual experience as `miru run` and `miru chat` streaming

- **Markdown rendering** in `miru run --no-stream`
  - Non-streaming mode now formats Markdown responses
  - Headers, code blocks, lists rendered with Rich
  - Consistent with streaming mode experience

### Changed

#### Improved User Experience

- **History command** (`miru history show`) now displays Markdown responses beautifully
  - Before: Plain text `**bold**` and `# headers`
  - After: Rich formatted **bold** and proper headers

- **Run command** (`miru run --no-stream`) renders Markdown
  - Before: Raw Markdown syntax in output
  - After: Formatted headers, code blocks, lists

#### Code Quality

- Added `render_markdown()` to commands that display complete responses
- Consistent Markdown formatting across all output modes
- Better separation between streaming (can't render Markdown progressively) and non-streaming (can render full Markdown)

### Documentation

- **Updated README.md**:
  - Added `/recall` command documentation
  - Updated chat commands section
  - Added examples of recall functionality

- **Updated TUTORIAL.md**:
  - Added recall command tutorial
  - Improved history section

### Technical Details

#### Files Modified

- `miru/commands/chat.py`:
  - Added `/recall` command handler
  - Interactive prompt selection with history
  - Direct index-based recall
  - Full i18n support

- `miru/commands/history_cmd.py`:
  - Added `render_markdown()` import
  - Response display uses Rich Markdown formatting

- `miru/commands/run.py`:
  - Added `render_markdown()` import
  - Non-streaming mode renders Markdown (when not quiet/JSON)

- `miru/core/i18n.py`:
  - Added 5 new i18n keys for recall feature:
    - `chat.commands.recall`
    - `chat.recall_title`
    - `chat.recall_empty`
    - `chat.recall_prompt`
    - `chat.recall_loaded`

### Migration Guide

#### Before (Plain Text History)

```bash
$ miru history show 0

Prompt:
Qual é o verso bíblico mais conhecido?

Response:
# Resposta com Markdown

Aqui está uma explicação:

## Código de Exemplo
```python
def soma(a, b):
    return a + b
```
```

#### After (Formatted Markdown)

```bash
$ miru history show 0

Prompt:
Qual é o verso bíblico mais conhecido?

Response:
                           Resposta com Markdown                           

Aqui está uma explicação:

Código de Exemplo

                                                                                
 def soma(a, b):                                                               
     return a + b                                                               
                                                                                
```

---

## [0.4.0] - 2026-04-07

### Added

#### Internationalization (i18n) - Full Support

- **Complete i18n system** with translations for Portuguese (Brazil), English, and Spanish
- **80+ translatable messages** across all categories (errors, success, suggestions, etc.)
- **Auto-detection** of system language via `LANG` environment variable
- **Manual override** via `MIRU_LANG` environment variable
- **Configurable** via `~/.miru/config.toml` (`language` setting)

```bash
# Use in Portuguese
export MIRU_LANG=pt_BR
miru run gemma3 "teste"
# ✗ Modelo 'gemma3' não encontrado.

# Use in English  
export MIRU_LANG=en_US
miru run gemma3 "test"
# ✗ Model 'gemma3' not found.

# Use in Spanish
export MIRU_LANG=es_ES
miru run gemma3 "prueba"
# ✗ Modelo 'gemma3' no encontrado.
```

#### Core Module (`miru/core/`) - New Architecture

- **`config.py`** - Unified configuration with caching
  - Single source of truth for all settings
  - Profile support for multiple environments
  - Language preference in config
  - Clear precedence: CLI > Env > Config > Default

- **`errors.py`** - Custom exception hierarchy
  - `MiruError` base class with suggestions
  - `ModelNotFoundError` - Lists available models
  - `ConnectionError` - Suggests `ollama serve`
  - `ValidationError`, `ToolExecutionError`, `ConfigError`

- **`i18n.py`** - Internationalization system
  - `t()` function for translations with parameters
  - `set_language()`, `get_language()`, `detect_language()`
  - `init_i18n()` auto-initialization on import

#### UI Module (`miru/ui/`) - Separation of Concerns

- **`render.py`** - Consistent output formatting
  - `render_error()`, `render_success()`, `render_warning()`, `render_info()`
  - Full i18n support with `t()` integration
  - `render_model_table()`, `render_metrics()`

- **`progress.py`** - Progress reporting
  - `ProgressReporter` class for all progress needs
  - Context manager `track_progress()`
  - Rich-based progress bars with spinners

- **`prompts.py`** - Interactive inputs
  - `confirm()`, `prompt_input()`, `prompt_choice()`

#### CLI Improvements

- **Standardized short flags** across all commands
  - `-h` for `--host`
  - `-f` for `--format` / `--file`
  - `-s` for `--system`
  - `-i` for `--image`
  - `-t` for `--temperature`
  - `-q` for `--quiet`
  - `-m` for `--max-tokens`

#### Testing

- **87 unit tests** for new modules
  - `test_core_i18n.py` - 21 tests
  - `test_core_errors.py` - 21 tests  
  - `test_core_config.py` - 28 tests
  - `test_ui_render.py` - 17 tests

- **19 integration tests** for i18n commands
  - `test_commands_i18n.py` - All passing

### Changed

#### Refactored Commands

All major commands now use `core/`, `ui/`, and `i18n` modules:

- **`run.py`** - Full i18n support, error handling with suggestions
- **`chat.py`** - Refactored with i18n and locale-aware messages
- **`compare.py`** - Locale-aware table headers and error messages
- **`batch.py`** - Processing status with i18n support
- **`list.py`** - Connection error with i18n
- **`info.py`** - Model not found with i18n suggestions
- **`pull.py`** - Download progress with locale messages
- **`delete.py`** - Confirmation and error with i18n
- **`copy.py`** - Success/error messages with i18n

#### Improved Architecture

- **Backward compatibility** - `config_manager.py` wraps `core/config.py`
- **Separation** - UI (console, Rich) isolated from business logic
- **Testability** - Modular design enables unit testing
- **Consistency** - All errors use `t()` for i18n

### Documentation

- **NEW: `docs/REFACTORING.md`** - Migration guide
- **UPDATED: `README.md`** - i18n examples
- **UPDATED: `CHANGELOG.md`** - Complete 0.4.0 changes

### Migration Guide

#### Before (Hardcoded PT-BR)

```python
console.print(f"[red bold]✗[/] Modelo '{model}' não encontrado.")
```

#### After (i18n)

```python
from miru.core.i18n import t
from miru.ui.render import render_error

render_error(t("error.model_not_found", model=model))
```

---
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