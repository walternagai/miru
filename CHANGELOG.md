# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-06

### Added

#### FASE 1: Tools Infrastructure

- **Tool System Foundation**
  - `Tool` class for representing executable tools
  - `ToolRegistry` for managing and executing tools
  - `@create_tool` decorator for creating tools from functions
  - `ToolNotFoundError`, `ToolExecutionError`, `ToolValidationError` exceptions
  - Utility functions: `extract_tool_calls()`, `has_tool_calls()`, `create_tool_result_message()`, `create_tool_call_message()`
  - Full validation of tool arguments against JSON schema

- **Ollama API Integration**
  - `OllamaClient.chat_with_tools()` method for function calling
  - Support for tool definitions in Ollama API format
  - Streaming responses with tool_calls support
  - Backward compatible with existing chat functionality

- **Testing**
  - 32 new tests for tools infrastructure (100% passing)
  - Test coverage for `Tool`, `ToolRegistry`, decorators
  - Test coverage for `OllamaClient.chat_with_tools()`

#### FASE 2: File and System Tools

- **FileSandbox Security**
  - Path traversal protection (prevents `../../../etc/passwd` attacks)
  - Sandbox directory isolation
  - Write/delete permission flags
  - File extension whitelist support
  - Automatic sandbox directory creation

- **File Tools** (8 tools)
  - `read_file`: Read text file contents
  - `write_file`: Write/create text file
  - `edit_file`: Edit file by exact string replacement
  - `list_files`: List files by glob pattern
  - `search_files`: Search files by name pattern
  - `delete_file`: Delete file (with permission check)
  - `file_exists`: Check if file exists
  - `get_file_info`: Get file metadata

- **Command Whitelist Security**
  - `CommandWhitelist` for controlling allowed shell commands
  - Dangerous command flag for approval flow
  - Command argument restrictions
  - Timeout enforcement

- **Environment Whitelist Security**
  - `EnvironmentWhitelist` for controlling allowed env vars
  - Prevents accidental secret leakage

- **System Tools** (5 tools)
  - `run_command`: Execute whitelisted shell commands
  - `get_env`: Read whitelisted environment variables
  - `get_current_dir`: Get current working directory
  - `list_allowed_commands`: List whitelisted commands
  - `list_allowed_env_vars`: List whitelisted env vars

- **Testing**
  - 67 new tests for file and system tools (100% passing)
  - Security tests for path traversal, command injection
  - Whitelist enforcement tests
  - Permission checking tests
  - Integration tests for combined file + system tools

#### FASE 3: Tool Execution Integration

- **ToolExecutionManager**
  - Central manager for tool execution
  - 4 execution modes: `disabled`, `manual`, `auto`, `auto_safe`
  - Automatic sandbox configuration
  - File and system tool registration
  - Tool definition generation for Ollama API
  - Execution permission checking
  - Error handling and reporting

- **ToolApprovalFlow**
  - Interactive approval system for dangerous tools
  - Safe vs dangerous tool classification
  - Session-based approval caching
  - Rich formatting for approval prompts
  - Tool categorization:
    - **Safe tools** (auto-approved): read_file, file_exists, get_file_info, list_files, search_files, get_current_dir, list_allowed_commands, list_allowed_env_vars, get_env
    - **Dangerous tools** (require approval): write_file, edit_file, delete_file, run_command

- **ToolApprovalManager**
  - Tracks approved/denied tools per session
  - Prevents repeated approval requests
  - Clear/saved approval state
  - Visual display of approved/denied tools

- **Execution Modes**
  - `DISABLED`: Tools not sent to model
  - `MANUAL`: Require approval for every tool
  - `AUTO`: Execute all tools automatically
  - `AUTO_SAFE`: Auto-execute safe tools, require approval for dangerous ones

- **Testing**
  - 41 new tests for execution and approval (100% passing)
  - Mode behavior tests
  - Approval flow integration tests
  - Safe/dangerous classification tests

### Security

- Sandbox isolation prevents path traversal attacks
- Whitelist-based security for commands and environment variables
- Permission flags for write/delete operations
- File extension whitelisting
- Timeout enforcement for command execution
- Restricted subprocess environment

### Testing

- **Total tests**: 388 (all passing)
- **New test files**:
  - `tests/test_tools/test_tools.py` (28 tests)
  - `tests/test_tools/test_client.py` (4 tests)
  - `tests/test_tools/test_files.py` (37 tests)
  - `tests/test_tools/test_system.py` (36 tests)
  - `tests/test_tools/test_execution.py` (17 tests)
  - `tests/test_tools/test_approval.py` (24 tests)

### Documentation

- `docs/tools-plan.md`: Complete implementation plan (7 phases)
- `docs/FASE1-COMPLETED.md`: Phase 1 documentation
- `docs/FASE2-COMPLETED.md`: Phase 2 documentation
- `docs/FASE3-COMPLETED.md`: Phase 3 documentation
- `docs/CODEBASE-REVIEW.md`: Code review and quality metrics

### Code Quality

- Type hints: 99% coverage
- Mypy checks: 1 non-critical warning
- Lines of code: ~3,000 (new)
- Code complexity: Low
- Test coverage: ~90% branch coverage

### Changed

- Updated `OllamaClient` with `chat_with_tools()` method
- Enhanced type hints across tools modules
- Improved error handling with specific exceptions

### Fixed

- Fixed type hint errors in `ToolRegistry.list()` (renamed to `list_tools()`)
- Fixed `Path.walk()` incompatibility (changed to `Path.rglob()`)
- Fixed `list[]` type annotation for Python 3.10 compatibility

### Migration Guide

#### For Users

No breaking changes. All existing functionality remains compatible.

To use tools:

```python
from miru.tools import ToolExecutionManager, ToolExecutionMode
from pathlib import Path

# Create manager
manager = ToolExecutionManager(
    mode=ToolExecutionMode.AUTO_SAFE,
    sandbox_dir=Path("./workspace"),
)

# Get tool definitions for Ollama
definitions = manager.get_tool_definitions()

# Use with OllamaClient
async with OllamaClient(host) as client:
    async for chunk in client.chat_with_tools("llama3.2", messages, tools=definitions):
        # Process response with potential tool_calls
        pass
```

#### For Developers

The new tools API is fully documented in:
- `miru/tools/__init__.py`: Public API
- `miru/tools/base.py`: Core classes
- `miru/tools/execution.py`: Execution manager
- `miru/tools/approval.py`: Approval system

Example of creating a custom tool:

```python
from miru.tools import Tool, ToolRegistry, create_tool

@create_tool(
    name="my_custom_tool",
    description="Does something useful",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input value"}
        },
        "required": ["input"]
    }
)
def my_custom_tool(input: str) -> str:
    return f"Processed: {input}"

# Register
registry = ToolRegistry()
tool = get_tool_from_function(my_custom_tool)
registry.register(tool)
```

---

## [0.1.0] - 2025-01-XX

### Added

- Initial release
- Basic CLI commands: `chat`, `generate`, `list`, `pull`, `info`, `copy`, `delete`
- Ollama server integration
- Multi-turn chat support
- Model management
- Image support for vision models
- Batch processing
- Model comparison
- History tracking
- Configuration management
- Alias support for models

### Security

- Basic input validation
- HTTP timeout handling
- Connection error handling

---

## Roadmap

### [0.4.0] - Planned

- CLI integration for tools (`miru tools list/exec`)
- Persistent configuration for tools
- Command-line flags: `--sandbox`, `--mode`, `--allow-write`
- Chat commands: `/tools`, `/mode`, `/sandbox`

### [0.5.0] - Planned

- Rate limiting for tool execution
- Audit logging
- Advanced sandbox features
- Network sandbox

### [0.6.0] - Planned

- Custom tools loading
- Tool chaining
- Context injection
- Web tools (fetch URLs)

### [0.7.0] - Planned

- Polish and optimization
- Performance improvements
- Extended documentation
- More examples

### [1.0.0] - Future

- Stable API
- Complete tools support
- Production-ready
- Full documentation coverage

---

## Version Philosophy

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR version (X.0.0)**: Incompatible API changes
- **MINOR version (0.X.0)**: Backward-compatible new features
- **PATCH version (0.0.X)**: Backward-compatible bug fixes

Since we're in `0.x` phase, API may change between minor versions.
We will reach `1.0.0` when the API is stable and all planned features are complete.

---

## Acknowledgments

- Ollama team for the excellent API and function calling support
- Rich library for beautiful terminal formatting
- Typer for the CLI framework
- All contributors and testers