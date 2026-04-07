"""Examples browser for miru CLI."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.core.i18n import t

console = Console()

EXAMPLES = {
    "hello-world": {
        "title": "Hello World",
        "description": "Basic prompt example",
        "command": 'miru run gemma3:latest "Hello, world!"',
        "tags": ["basic", "beginner"],
        "category": "basics",
    },
    "code-python": {
        "title": "Python Code Generation",
        "description": "Generate Python code",
        "command": 'miru run gemma3:latest "Write a Python function to sort a list" --system "You are a Python expert"',
        "tags": ["code", "python"],
        "category": "code",
    },
    "code-javascript": {
        "title": "JavaScript Code Generation",
        "description": "Generate JavaScript code",
        "command": 'miru run qwen2.5:7b "Write a JavaScript function to fetch API data" --system "You are a JavaScript expert"',
        "tags": ["code", "javascript"],
        "category": "code",
    },
    "summarize-article": {
        "title": "Summarize Article",
        "description": "Summarize long text",
        "command": 'miru run gemma3:latest --file article.txt "Summarize this article in 3 bullet points"',
        "tags": ["text", "summarize"],
        "category": "text",
    },
    "translate-pt": {
        "title": "Translate to Portuguese",
        "description": "Translate text to Portuguese",
        "command": 'miru quick translate-pt gemma3:latest --param text="Hello world"',
        "tags": ["translate", "portuguese"],
        "category": "translation",
    },
    "review-code": {
        "title": "Code Review",
        "description": "Review code for improvements",
        "command": 'miru quick review-code gemma3:latest --param language=python --param code="$(cat main.py)"',
        "tags": ["code", "review"],
        "category": "code",
    },
    "explain-topic": {
        "title": "Explain a Topic",
        "description": "Get explanation of complex topics",
        "command": 'miru quick explain gemma3:latest --param topic="machine learning"',
        "tags": ["explain", "learning"],
        "category": "learning",
    },
    "fix-code": {
        "title": "Fix Code Bugs",
        "description": "Find and fix bugs in code",
        "command": 'miru quick fix-code gemma3:latest --param language=python --param code="$(cat broken.py)"',
        "tags": ["code", "debug"],
        "category": "code",
    },
    "generate-tests": {
        "title": "Generate Unit Tests",
        "description": "Create unit tests for code",
        "command": 'miru quick test gemma3:latest --param language=python --param code="$(cat main.py)"',
        "tags": ["code", "testing"],
        "category": "code",
    },
    "chat-interactive": {
        "title": "Interactive Chat",
        "description": "Start a chat session",
        "command": 'miru chat gemma3:latest --system "You are a helpful assistant"',
        "tags": ["chat", "interactive"],
        "category": "chat",
    },
    "compare-models": {
        "title": "Compare Models",
        "description": "Compare responses from multiple models",
        "command": 'miru compare gemma3:latest qwen2.5:7b --prompt "What is closure?"',
        "tags": ["benchmark", "compare"],
        "category": "advanced",
    },
    "vision-describe": {
        "title": "Describe Image",
        "description": "Use vision model to describe image",
        "command": 'miru run llava:latest "Describe this image" --image photo.jpg',
        "tags": ["vision", "image"],
        "category": "multimodal",
    },
    "analyze-document": {
        "title": "Analyze Document",
        "description": "Analyze PDF or document",
        "command": 'miru run gemma3:latest --file report.pdf "Summarize key findings"',
        "tags": ["document", "pdf"],
        "category": "document",
    },
    "batch-processing": {
        "title": "Batch Processing",
        "description": "Process multiple prompts",
        "command": "miru batch gemma3:latest --prompts prompts.txt --format json",
        "tags": ["batch", "automation"],
        "category": "advanced",
    },
    "embed-text": {
        "title": "Generate Embeddings",
        "description": "Create text embeddings",
        "command": 'miru embed nomic-embed-text "Hello world" --format json',
        "tags": ["embed", "vector"],
        "category": "advanced",
    },
    "template-save": {
        "title": "Save Template",
        "description": "Create reusable prompt template",
        "command": 'miru template save code-review --prompt "Review this code: {code}" --description "Code review template"',
        "tags": ["template", "reuse"],
        "category": "templates",
    },
    "config-profile": {
        "title": "Configuration Profile",
        "description": "Create configuration profile",
        "command": "miru config profile create work\nmiru config set default_host http://work-server:11434",
        "tags": ["config", "profile"],
        "category": "config",
    },
    "save-session": {
        "title": "Save Chat Session",
        "description": "Save conversation for later",
        "command": "miru chat gemma3:latest\n# then use /save command inside chat",
        "tags": ["session", "save"],
        "category": "chat",
    },
}


def examples_list(category: str | None = None, tag: str | None = None) -> None:
    """List available examples."""
    filtered = {}

    for key, example in EXAMPLES.items():
        if category and example.get("category") != category:
            continue
        if tag and tag not in example.get("tags", []):
            continue
        filtered[key] = example

    if not filtered:
        console.print(f"[yellow]{t('examples.no_examples')}[/]")
        return

    table = Table(title=t("examples.title"), show_header=True, header_style="bold cyan")
    table.add_column(t("examples.key_header"), style="green")
    table.add_column(t("examples.title_header"))
    table.add_column(t("examples.category_header"))
    table.add_column(t("examples.tags_header"))

    for key, example in sorted(filtered.items()):
        tags = ", ".join(example.get("tags", []))[:30]
        table.add_row(
            key,
            example.get("title", ""),
            example.get("description", "")[:40],
            example.get("category", ""),
            tags,
        )

    console.print(table)


def examples_show(name: str, copy: bool = False) -> None:
    """Show example details."""
    if name not in EXAMPLES:
        console.print(f"[red bold]✗[/] {t('examples.not_found', name=name)}")
        console.print(f"[dim]{t('examples.use_list')}[/]")
        sys.exit(1)

    example = EXAMPLES[name]

    console.print(f"[bold]{example.get('title', name)}[/]")
    console.print()
    console.print(f"[dim]{t('examples.desc_label')}[/] {example.get('description', '')}")
    console.print(f"[dim]{t('examples.category_label')}[/] {example.get('category', '')}")
    console.print(f"[dim]{t('examples.tags_label')}[/] {', '.join(example.get('tags', []))}")
    console.print()

    console.print(f"[bold]{t('examples.command_label')}[/]")
    console.print(f"  [cyan]{example.get('command', '')}[/]")
    console.print()

    if copy:
        try:
            import pyperclip

            pyperclip.copy(example.get("command", ""))
            console.print(f"[green]✓[/] {t('examples.copied')}")
        except ImportError:
            console.print(
                f"[yellow]{t('examples.install_pyperclip')}[/]"
            )
            console.print(f"[dim]{t('examples.command_shown')}[/]")


def examples_categories() -> None:
    """List example categories."""
    categories = {}

    for example in EXAMPLES.values():
        cat = example.get("category", "other")
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

    table = Table(title=t("examples.categories_title"), show_header=True, header_style="bold cyan")
    table.add_column(t("examples.category_header"), style="green")
    table.add_column(t("examples.examples_count"), justify="right")

    for cat, count in sorted(categories.items()):
        table.add_row(cat, str(count))

    console.print(table)


def examples(
    name: Annotated[str | None, typer.Argument(help="Example name")] = None,
    list_examples: Annotated[bool, typer.Option("--list", "-l", help="List all examples")] = False,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Filter by category")
    ] = None,
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag")] = None,
    copy: Annotated[bool, typer.Option("--copy", help="Copy command to clipboard")] = False,
    categories: Annotated[bool, typer.Option("--categories", help="List categories")] = False,
) -> None:
    """Browse and view usage examples.

    Examples:
        miru examples --list
        miru examples --category code
        miru examples hello-world
        miru examples hello-world --copy
        miru examples --categories
    """
    if categories:
        examples_categories()
        return

    if list_examples:
        examples_list(category, tag)
        return

    if name:
        examples_show(name, copy)
        return

    if category or tag:
        examples_list(category, tag)
        return

    console.print(f"[bold]{t('examples.browser_title')}[/]")
    console.print()
    console.print(f"[dim]{t('examples.use_list_help')}[/]")
    console.print(f"[dim]{t('examples.use_category_help')}[/]")
    console.print(f"[dim]{t('examples.use_tag_help')}[/]")
    console.print(f"[dim]{t('examples.use_name_help')}[/]")
    console.print(f"[dim]{t('examples.use_copy_help')}[/]")
    console.print()
    console.print(f"[bold]{t('examples.popular_examples')}[/]")
    for key in ["hello-world", "code-python", "chat-interactive", "compare-models"]:
        example = EXAMPLES[key]
        console.print(f"  • {key}: {example.get('title', '')}")
    console.print()
    console.print(f"[dim]{t('examples.full_list')}[/]")