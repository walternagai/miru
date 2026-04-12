"""Quick commands for common tasks."""

import asyncio
import sys
from typing import Annotated

import typer
from rich.console import Console

from miru.alias import resolve_alias
from miru.config import get_host
from miru.config_manager import load_config
from miru.inference_params import build_options
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound
from miru.core.i18n import t

console = Console()

QUICK_COMMANDS = {
    "code": {
        "prompt": "Write {language} code to: {task}. Provide clean, well-commented code.",
        "description": "Generate code",
        "system": "You are an expert programmer. Write clean, efficient, well-documented code.",
    },
    "translate-pt": {
        "prompt": "Translate to Portuguese: {text}",
        "description": "Translate text to Portuguese",
        "system": "You are a professional translator. Preserve the meaning and tone.",
    },
    "translate-en": {
        "prompt": "Translate to English: {text}",
        "description": "Translate text to English",
        "system": "You are a professional translator. Preserve the meaning and tone.",
    },
    "summarize": {
        "prompt": "Summarize the following text concisely, highlighting key points:\n\n{text}",
        "description": "Summarize text",
        "system": "You are an expert summarizer. Be concise and capture essential information.",
    },
    "explain": {
        "prompt": "Explain {topic} in simple terms with examples.",
        "description": "Explain a topic",
        "system": "You are a patient teacher. Explain concepts clearly with practical examples.",
    },
    "fix-code": {
        "prompt": "Fix the bugs in this {language} code:\n```{language}\n{code}\n```\n\nProvide the corrected code and explain what was wrong.",
        "description": "Fix code bugs",
        "system": "You are an expert debugger. Identify and fix issues while explaining your changes.",
    },
    "review-code": {
        "prompt": "Review this {language} code for best practices, potential bugs, and improvements:\n```{language}\n{code}\n```\n\nProvide specific, actionable feedback.",
        "description": "Code review",
        "system": "You are a senior code reviewer. Focus on code quality, maintainability, and potential issues.",
    },
    "refactor": {
        "prompt": "Refactor this {language} code to be more clean, efficient, and maintainable:\n```{language}\n{code}\n```\n\nExplain your refactoring decisions.",
        "description": "Refactor code",
        "system": "You are an expert in clean code principles. Improve code structure and readability.",
    },
    "test": {
        "prompt": "Write comprehensive unit tests for this {language} code:\n```{language}\n{code}\n```\n\nInclude edge cases and error handling.",
        "description": "Generate unit tests",
        "system": "You are a test-driven development expert. Write thorough, meaningful tests.",
    },
    "document": {
        "prompt": "Write comprehensive documentation for this {language} code:\n```{language}\n{code}\n```\n\nInclude usage examples, parameters, and return values.",
        "description": "Generate documentation",
        "system": "You are a technical writer. Create clear, comprehensive documentation.",
    },
    "optimize": {
        "prompt": "Optimize this {language} code for better performance:\n```{language}\n{code}\n```\n\nExplain the optimizations and their impact.",
        "description": "Optimize code",
        "system": "You are a performance optimization expert. Focus on algorithmic and memory efficiency.",
    },
    "analyze": {
        "prompt": "Analyze the following text for tone, sentiment, key themes, and writing style:\n\n{text}",
        "description": "Analyze text",
        "system": "You are a literary analyst. Provide detailed, nuanced analysis.",
    },
    "grammar": {
        "prompt": "Fix grammar and spelling errors in this text while preserving meaning:\n\n{text}",
        "description": "Fix grammar",
        "system": "You are an expert editor. Fix errors while maintaining the author's voice.",
    },
    "expand": {
        "prompt": "Expand this text with more details and examples:\n\n{text}",
        "description": "Expand text",
        "system": "You are a creative writer. Add depth and clarity while maintaining coherence.",
    },
    "simplify": {
        "prompt": "Simplify this text for a general audience:\n\n{text}",
        "description": "Simplify text",
        "system": "You are an expert at making complex topics accessible. Use clear, simple language.",
    },
}


async def _run_quick_command_async(
    command: str,
    model: str,
    params: dict[str, str],
    host: str,
    format: str,
    quiet: bool,
) -> None:
    """Async implementation of quick command."""
    command_data = QUICK_COMMANDS.get(command)
    if not command_data:
        console.print(f"[red bold]✗[/] {t('quick.unknown_command', command=command)}")
        console.print(f"[dim]{t('quick.available_commands', commands=', '.join(QUICK_COMMANDS.keys()))}[/]")
        sys.exit(1)

    prompt_template = command_data["prompt"]
    system = command_data.get("system")

    try:
        prompt = prompt_template.format(**params)
    except KeyError as e:
        console.print(f"[red bold]✗[/] {t('quick.missing_parameter', param=e)}")
        console.print(
            f"[dim]{t('quick.required_params', command=command, params=', '.join(_extract_params(prompt_template)))}[/]"
        )
        sys.exit(1)

    model = resolve_alias(model)

    async with OllamaClient(host) as client:
        try:
            all_models = await client.list_models()
            model_names = [m.get("name", "") for m in all_models]
            if model not in model_names:
                console.print(f"[red bold]✗[/] {t('error.model_not_found', model=model)}")
                console.print(f"[dim]{t('suggestion.pull_model', model=model)}[/]")
                sys.exit(1)

            options = build_options()
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response_parts = []
            final_chunk = None

            chunks = client.chat(model, messages, options=options, stream=True)
            async for chunk in chunks:
                content = chunk.get("message", {}).get("content", "")
                if content:
                    print(content, end="", flush=True)
                    response_parts.append(content)
                if chunk.get("done"):
                    final_chunk = chunk

            print()

            if final_chunk and not quiet:
                eval_count = final_chunk.get("eval_count", 0)
                eval_duration_ns = final_chunk.get("eval_duration", 0)
                eval_seconds = eval_duration_ns / 1e9
                tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
                print(f"\n[{eval_count} tokens · {tokens_per_second:.1f} tok/s]")

        except OllamaModelNotFound:
            console.print(f"[red bold]✗[/] {t('error.model_not_found', model=model)}")
            console.print(f"[dim]{t('suggestion.pull_model', model=model)}[/]")
            sys.exit(1)
        except OllamaConnectionError as e:
            console.print(f"[red bold]✗[/] {e}")
            sys.exit(1)


def _extract_params(template: str) -> list[str]:
    """Extract parameter names from template."""
    import re

    return re.findall(r"\{(\w+)\}", template)


def quick_list() -> None:
    """List available quick commands."""
    table = console.Table(title=t("quick.title"), show_header=True, header_style="bold cyan")
    table.add_column(t("quick.command_header"), style="green")
    table.add_column(t("quick.description_header"))
    table.add_column(t("quick.params_header"))

    for cmd, data in sorted(QUICK_COMMANDS.items()):
        params = ", ".join(_extract_params(data["prompt"]))
        table.add_row(f"miru quick {cmd}", data["description"], params if params else "—")

    console.print(table)
    console.print()
    console.print(f"[dim]{t('quick.usage')}")
    console.print(
        f"[dim]{t('quick.example')}[/]"
    )


def quick(
    command: Annotated[str, typer.Argument(help="Quick command name")],
    model: Annotated[str | None, typer.Argument(help="Model name")] = None,
    param: Annotated[
        list[str], typer.Option("--param", "-p", help="Parameter in KEY=VALUE format")
    ] = [],
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format")] = "text",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Minimal output")] = False,
    list_commands: Annotated[
        bool, typer.Option("--list", "-l", help="List available commands")
    ] = False,
) -> None:
    """Run quick commands for common tasks.

    \b
    Available commands:
        code        - Generate code
        translate-pt - Translate to Portuguese
        translate-en - Translate to English
        summarize   - Summarize text
        explain     - Explain a topic
        fix-code    - Fix code bugs
        review-code - Code review
        refactor    - Refactor code
        test        - Generate unit tests
        document    - Generate documentation
        optimize    - Optimize code
        analyze     - Analyze text
        grammar     - Fix grammar
        expand      - Expand text
        simplify    - Simplify text

    \b
    Examples:
        miru quick code gemma3 --param language=python --param task="sort list"
        miru quick summarize gemma3 --param text="Long article..."
        miru quick explain gemma3 --param topic="machine learning"
    """
    if list_commands:
        quick_list()
        return

    if command == "list":
        quick_list()
        return

    if model is None:
        config = load_config()
        model = config.default_model
        if model is None:
            console.print(f"[red bold]✗[/] {t('prompt.model_required')}")
            console.print(f"[dim]{t('prompt.use_specify', command='quick <command> <model>')}")
            console.print(f"[dim]{t('prompt.or_configure')}")
            sys.exit(1)

    params_dict: dict[str, str] = {}
    for param_str in param:
        if "=" not in param_str:
            console.print(f"[red bold]✗[/] {t('quick.invalid_param', param=param_str)}")
            sys.exit(1)
        key, value = param_str.split("=", 1)
        params_dict[key] = value

    # Auto-fill primary parameter from stdin when piped
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()
        if stdin_content:
            command_data = QUICK_COMMANDS.get(command, {})
            template = command_data.get("prompt", "")
            template_params = _extract_params(template)
            for primary_key in ("text", "code", "topic"):
                if primary_key in template_params and primary_key not in params_dict:
                    params_dict[primary_key] = stdin_content
                    break

    resolved_host = get_host(host)

    try:
        asyncio.run(
            _run_quick_command_async(
                command=command,
                model=model,
                params=params_dict,
                host=resolved_host,
                format=format,
                quiet=quiet,
            )
        )
    except KeyboardInterrupt:
        print()
        sys.exit(0)