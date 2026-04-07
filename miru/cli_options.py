"""Common CLI options with consistent short flags.

Provides reusable Typer options with standardized short flags across all commands.
"""

from typing import Annotated

import typer

from miru.core.i18n import t

# Host option
Host = Annotated[
    str | None,
    typer.Option("--host", "-h", help="Ollama host URL"),
]

# Output format option
Format = Annotated[
    str,
    typer.Option("--format", "-f", help="Output format (text/json/jsonl)"),
]

# Quiet option
Quiet = Annotated[
    bool,
    typer.Option("--quiet", "-q", help="Minimal output"),
]

# Verbose option
Verbose = Annotated[
    bool,
    typer.Option("--verbose", "-v", help="Verbose output"),
]

# Model option (positional)
Model = Annotated[
    str,
    typer.Argument(help="Model name"),
]

# Model option (optional)
ModelOptional = Annotated[
    str | None,
    typer.Argument(help="Model name"),
]

# Prompt option
Prompt = Annotated[
    str,
    typer.Argument(help="Prompt text"),
]

# System prompt option
SystemPrompt = Annotated[
    str | None,
    typer.Option("--system", "-s", help="System prompt to set model behavior"),
]

# System prompt file option
SystemPromptFile = Annotated[
    str | None,
    typer.Option("--system-file", help="Read system prompt from file"),
]

# Image files option (repeatable)
ImageFiles = Annotated[
    list[str],
    typer.Option("--image", "-i", help="Image file (repeatable)"),
]

# Input files option (repeatable)
InputFiles = Annotated[
    list[str],
    typer.Option("--file", "-f", help="Input file (repeatable)"),
]

# Audio file option
AudioFile = Annotated[
    str | None,
    typer.Option("--audio", "-a", help="Audio file for transcription"),
]

# Temperature option
Temperature = Annotated[
    float | None,
    typer.Option("--temperature", "-t", help="Sampling temperature (0.0-2.0)"),
]

# Max tokens option
MaxTokens = Annotated[
    int | None,
    typer.Option("--max-tokens", "-m", help="Maximum tokens to generate"),
]

# Top-p option
TopP = Annotated[
    float | None,
    typer.Option("--top-p", "-p", help="Nucleus sampling probability (0.0-1.0)"),
]

# Top-k option
TopK = Annotated[
    int | None,
    typer.Option("--top-k", "-k", help="Top-k sampling"),
]

# Seed option
Seed = Annotated[
    int | None,
    typer.Option("--seed", help="Random seed for reproducibility"),
]

# Repeat penalty option
RepeatPenalty = Annotated[
    float | None,
    typer.Option("--repeat-penalty", help="Repetition penalty"),
]

# Context window option
Context = Annotated[
    int | None,
    typer.Option("--ctx", "-c", help="Context window size"),
]

# Timeout option
Timeout = Annotated[
    float | None,
    typer.Option("--timeout", help="Request timeout in seconds"),
]

# Auto-pull option
AutoPull = Annotated[
    bool,
    typer.Option("--auto-pull", help="Auto-download model if missing"),
]

# No-stream option
NoStream = Annotated[
    bool,
    typer.Option("--no-stream", help="Disable streaming output"),
]

# Force option
Force = Annotated[
    bool,
    typer.Option("--force", "-f", help="Skip confirmation"),
]

# Dry-run option
DryRun = Annotated[
    bool,
    typer.Option("--dry-run", help="Show what would be done without executing"),
]

# Enable tools option
EnableTools = Annotated[
    bool,
    typer.Option("--enable-tools", help="Enable all tools (file, system, tavily)"),
]

# Enable Tavily option
EnableTavily = Annotated[
    bool,
    typer.Option("--tavily", help="Enable Tavily web search tool"),
]

# Sandbox directory option
SandboxDir = Annotated[
    str | None,
    typer.Option("--sandbox-dir", help="Sandbox directory for file tools"),
]

# Tool mode option
ToolMode = Annotated[
    str,
    typer.Option("--tool-mode", help="Tool execution mode (manual/auto/auto_safe)"),
]

# Limit option
Limit = Annotated[
    int,
    typer.Option("--limit", "-n", help="Number of entries"),
]

# Search query option
SearchQuery = Annotated[
    str | None,
    typer.Option("--search", "-s", help="Search query"),
]

# Command filter option
CommandFilter = Annotated[
    str | None,
    typer.Option("--command", "-c", help="Filter by command"),
]

# Output file option
OutputFile = Annotated[
    str | None,
    typer.Option("--output", "-o", help="Output file"),
]


def get_model_with_fallback(model: str | None) -> str:
    """Get model with fallback to config.
    
    Args:
        model: Model name from CLI or None
        
    Returns:
        Model name
        
    Raises:
        SystemExit: If no model specified and no default configured
    """
    if model:
        return model
    
    from miru.core.config import resolve_model
    
    default_model = resolve_model()
    if default_model:
        return default_model
    
    from miru.ui.render import render_error
    import sys
    
    render_error(
        t("prompt.model_required"),
        f"{t('prompt.use_specify', command='chat')}\n{t('prompt.or_configure')}",
    )
    sys.exit(1)