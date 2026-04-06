"""Template management for reusable prompts."""

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from miru.config_manager import TEMPLATE_DIR, ensure_config_dir

console = Console()


@dataclass
class PromptTemplate:
    """A reusable prompt template."""

    name: str
    prompt: str
    system_prompt: str | None = None
    description: str | None = None
    parameters: list[str] | None = None
    created_at: str | None = None
    modified_at: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptTemplate":
        """Create from dictionary."""
        return cls(**data)

    def render(self, **kwargs: Any) -> tuple[str, str | None]:
        """Render template with parameters.

        Returns:
            Tuple of (prompt, system_prompt)
        """
        prompt = self.prompt
        system = self.system_prompt

        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            prompt = prompt.replace(placeholder, str(value))
            if system:
                system = system.replace(placeholder, str(value))

        return prompt, system


def _get_template_path(name: str) -> Path:
    """Get template file path."""
    return TEMPLATE_DIR / f"{name}.json"


def _list_templates() -> list[PromptTemplate]:
    """List all available templates."""
    ensure_config_dir()

    templates = []

    if not TEMPLATE_DIR.exists():
        return templates

    for file in TEMPLATE_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                templates.append(PromptTemplate.from_dict(data))
        except Exception:
            continue

    templates.sort(key=lambda t: t.name)
    return templates


def _save_template(template: PromptTemplate) -> None:
    """Save template to file."""
    ensure_config_dir()

    path = _get_template_path(template.name)

    if template.created_at is None:
        template.created_at = datetime.now().isoformat()
    template.modified_at = datetime.now().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)


def _delete_template(name: str) -> bool:
    """Delete a template."""
    path = _get_template_path(name)

    if not path.exists():
        return False

    path.unlink()
    return True


app = typer.Typer(help="Manage prompt templates")


@app.command("list")
def template_list() -> None:
    """List all saved templates.

    Example:
        miru template list
    """
    templates = _list_templates()

    if not templates:
        console.print("[dim]Nenhum template salvo[/]")
        console.print("[dim]Crie um: miru template save <name> --prompt <prompt>[/]")
        return

    table = Table(title="Templates Salvos", show_header=True, header_style="bold cyan")
    table.add_column("Nome", style="green")
    table.add_column("Descrição")
    table.add_column("Parâmetros")

    for t in templates:
        params = ", ".join(t.parameters) if t.parameters else "—"
        desc = (
            t.description[:50] + "..."
            if t.description and len(t.description) > 50
            else (t.description or "—")
        )
        table.add_row(t.name, desc, params)

    console.print(table)


@app.command("save")
def template_save(
    name: Annotated[str, typer.Argument(help="Template name")],
    prompt: Annotated[str | None, typer.Option("--prompt", "-p", help="Prompt template")] = None,
    prompt_file: Annotated[
        str | None, typer.Option("--prompt-file", "-f", help="Read prompt from file")
    ] = None,
    system: Annotated[
        str | None, typer.Option("--system", "-s", help="System prompt template")
    ] = None,
    system_file: Annotated[
        str | None, typer.Option("--system-file", help="Read system prompt from file")
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Template description")
    ] = None,
    parameters: Annotated[
        str | None, typer.Option("--parameters", help="Comma-separated parameter names")
    ] = None,
) -> None:
    """Save a prompt template.

    Examples:
        miru template save code-review --prompt "Review this code: {code}" --description "Code review template"
        miru template save summarize --prompt-file prompt.txt --system "Be concise"
    """
    if prompt is None and prompt_file is None:
        console.print("[red bold]✗[/] É necessário fornecer --prompt ou --prompt-file")
        sys.exit(1)

    if prompt is not None and prompt_file is not None:
        console.print("[red bold]✗[/] Use --prompt OU --prompt-file, não ambos")
        sys.exit(1)

    if system is not None and system_file is not None:
        console.print("[red bold]✗[/] Use --system OU --system-file, não ambos")
        sys.exit(1)

    final_prompt: str
    if prompt_file:
        path = Path(prompt_file)
        if not path.exists():
            console.print(f"[red bold]✗[/] Arquivo não encontrado: {prompt_file}")
            sys.exit(1)
        final_prompt = path.read_text(encoding="utf-8").strip()
    else:
        final_prompt = prompt or ""

    final_system: str | None = None
    if system_file:
        path = Path(system_file)
        if not path.exists():
            console.print(f"[red bold]✗[/] Arquivo não encontrado: {system_file}")
            sys.exit(1)
        final_system = path.read_text(encoding="utf-8").strip()
    elif system:
        final_system = system.strip()

    param_list = [p.strip() for p in parameters.split(",")] if parameters else None

    template = PromptTemplate(
        name=name,
        prompt=final_prompt,
        system_prompt=final_system,
        description=description,
        parameters=param_list,
    )

    _save_template(template)

    console.print(f"[green bold]✓[/] Template '{name}' salvo")
    console.print(f"[dim]Local: {TEMPLATE_DIR / name}.json[/]")


@app.command("show")
def template_show(
    name: Annotated[str, typer.Argument(help="Template name")],
) -> None:
    """Show template details.

    Example:
        miru template show code-review
    """
    path = _get_template_path(name)

    if not path.exists():
        console.print(f"[red bold]✗[/] Template '{name}' não encontrado")
        console.print("[dim]Listar templates: miru template list[/]")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        template = PromptTemplate.from_dict(data)
    except Exception as e:
        console.print(f"[red bold]✗[/] Erro ao carregar template: {e}")
        sys.exit(1)

    console.print(f"[bold]Nome:[/] {template.name}")
    if template.description:
        console.print(f"[bold]Descrição:[/] {template.description}")
    if template.parameters:
        console.print(f"[bold]Parâmetros:[/] {', '.join(template.parameters)}")
    console.print()
    console.print("[bold]Prompt:[/]")
    console.print(template.prompt)
    if template.system_prompt:
        console.print()
        console.print("[bold]System Prompt:[/]")
        console.print(template.system_prompt)


@app.command("delete")
def template_delete(
    name: Annotated[str, typer.Argument(help="Template name")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """Delete a template.

    Example:
        miru template delete code-review
    """
    path = _get_template_path(name)

    if not path.exists():
        console.print(f"[red bold]✗[/] Template '{name}' não encontrado")
        sys.exit(1)

    if not force:
        console.print(f"[yellow]Deletar template '{name}'?[/] Use --force para confirmar")
        return

    _delete_template(name)
    console.print(f"[green bold]✓[/] Template '{name}' deletado")


@app.command("run")
def template_run(
    name: Annotated[str, typer.Argument(help="Template name")],
    model: Annotated[str, typer.Argument(help="Model name")] = None,
    params: Annotated[
        list[str], typer.Option("--param", "-p", help="Parameter in KEY=VALUE format")
    ] = [],
    extra_prompt: Annotated[
        str | None, typer.Option("--extra", help="Additional prompt text")
    ] = None,
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[str, typer.Option("--format", help="Output format (text/json)")] = "text",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Minimal output")] = False,
) -> None:
    """Run a template with parameters.

    Examples:
        miru template run code-review gemma3:latest --param code="def hello(): pass"
        miru template run summarize qwen2.5 --param text="Long article..."
    """
    import asyncio

    from miru.commands.run import run
    from miru.config_manager import resolve_host, load_config

    path = _get_template_path(name)

    if not path.exists():
        console.print(f"[red bold]✗[/] Template '{name}' não encontrado")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        template = PromptTemplate.from_dict(data)
    except Exception as e:
        console.print(f"[red bold]✗[/] Erro ao carregar template: {e}")
        sys.exit(1)

    params_dict: dict[str, str] = {}
    for param_str in params:
        if "=" not in param_str:
            console.print(f"[red bold]✗[/] Parâmetro inválido: {param_str}. Use KEY=VALUE")
            sys.exit(1)
        key, value = param_str.split("=", 1)
        params_dict[key] = value

    prompt, system = template.render(**params_dict)

    if extra_prompt:
        prompt = prompt + "\n\n" + extra_prompt

    if model is None:
        config = load_config()
        model = config.default_model
        if model is None:
            console.print("[red bold]✗[/] Model não especificado")
            console.print("[dim]Use: miru template run <template> <model>[/]")
            sys.exit(1)

    resolved_host = resolve_host(host)

    run(
        model=model,
        prompt=prompt,
        system=system,
        host=resolved_host,
        format=format,
        quiet=quiet,
    )


@app.command("export")
def template_export(
    name: Annotated[str, typer.Argument(help="Template name")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file")] = None,
) -> None:
    """Export template to file.

    Example:
        miru template export code-review --output template.json
    """
    import shutil

    path = _get_template_path(name)

    if not path.exists():
        console.print(f"[red bold]✗[/] Template '{name}' não encontrado")
        sys.exit(1)

    if output:
        shutil.copy(path, output)
        console.print(f"[green bold]✓[/] Template exported to {output}")
    else:
        with open(path, "r", encoding="utf-8") as f:
            print(f.read())


@app.command("import")
def template_import(
    file: Annotated[str, typer.Argument(help="Template file (JSON)")],
    name: Annotated[
        str | None, typer.Option("--name", "-n", help="Template name (override)")
    ] = None,
) -> None:
    """Import template from file.

    Example:
        miru template import template.json --name my-template
    """
    import shutil

    path = Path(file)

    if not path.exists():
        console.print(f"[red bold]✗[/] Arquivo não encontrado: {file}")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        template = PromptTemplate.from_dict(data)
    except Exception as e:
        console.print(f"[red bold]✗[/] Erro ao carregar template: {e}")
        sys.exit(1)

    if name:
        template.name = name

    _save_template(template)
    console.print(f"[green bold]✓[/] Template '{template.name}' importado")


app.command("export")(template_export)
app.command("import")(template_import)


def template() -> None:
    """Template command group entry point."""
    app()
