"""Tools command for managing function calling tools."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.tools import ToolRegistry, create_file_tools, create_system_tools
from miru.tools.files import FileSandbox
from miru.tools.system import CommandWhitelist, EnvironmentWhitelist

console = Console()
app = typer.Typer(help="Manage tools for function calling")


def _create_default_registry() -> ToolRegistry:
    """Create default tool registry with file and system tools."""
    registry = ToolRegistry()
    sandbox = FileSandbox(root=".")
    cmd_whitelist = CommandWhitelist()
    env_whitelist = EnvironmentWhitelist()

    for tool in create_file_tools(sandbox):
        registry.register(tool)

    for tool in create_system_tools(cmd_whitelist, env_whitelist):
        registry.register(tool)

    return registry


@app.command("list")
def tools_list(
    category: Annotated[
        str | None,
        typer.Option("--category", "-c", help="Filter by category (files/system)"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format (text/json)"),
    ] = "text",
) -> None:
    """List all available tools.

    Examples:
        miru tools list
        miru tools list --category files
        miru tools list --format json
    """
    registry = _create_default_registry()
    tools = registry.list_tools()

    if category:
        category_prefix = f"{category}_"
        tools = [t for t in tools if t.name.startswith(category_prefix)]

    if not tools:
        console.print("[yellow]No tools found[/]")
        return

    if format == "json":
        import json

        data = [
            {
                "name": tool.name,
                "description": tool.description[:50] + "..."
                if len(tool.description) > 50
                else tool.description,
                "parameters": tool.parameters.get("properties", {}),
            }
            for tool in tools
        ]
        console.print(json.dumps(data, indent=2))
        return

    table = Table(title="Available Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Parameters", style="dim")

    for tool in sorted(tools, key=lambda t: t.name):
        params = tool.parameters.get("required", [])
        params_str = ", ".join(params) if params else "-"
        desc = tool.description.split("\n")[0]
        if len(desc) > 60:
            desc = desc[:57] + "..."
        table.add_row(tool.name, desc, params_str)

    console.print(table)
    console.print()
    console.print(f"[dim]Total: {len(tools)} tools[/]")


@app.command("show")
def tools_show(
    name: Annotated[str, typer.Argument(help="Tool name")],
) -> None:
    """Show detailed information about a tool.

    Example:
        miru tools show read_file
    """
    registry = _create_default_registry()

    try:
        tool = registry.get(name)
    except Exception:
        console.print(f"[red bold]✗[/] Tool not found: {name}")
        console.print("[dim]Use 'miru tools list' to see available tools[/]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]{tool.name}[/]\n")
    console.print(f"[bold]Description:[/]")
    console.print(f"  {tool.description}\n")

    properties = tool.parameters.get("properties", {})
    required = tool.parameters.get("required", [])

    if properties:
        console.print("[bold]Parameters:[/]")
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "any")
            param_desc = param_info.get("description", "")
            is_required = param_name in required
            req_marker = "*" if is_required else ""
            console.print(f"  [cyan]{param_name}{req_marker}[/] ({param_type})")
            if param_desc:
                console.print(f"    [dim]{param_desc}[/]")

    console.print("\n[bold]Ollama Format:[/]")
    import json

    console.print(f"  {json.dumps(tool.to_ollama_format(), indent=2)}\n")


@app.command("exec")
def tools_exec(
    name: Annotated[str, typer.Argument(help="Tool name")],
    arg: Annotated[
        list[str],
        typer.Option("--arg", "-a", help="Arguments in KEY=VALUE format"),
    ] = [],
    json_input: Annotated[
        str | None,
        typer.Option("--json", "-j", help="JSON arguments"),
    ] = None,
) -> None:
    """Execute a tool directly.

    Examples:
        miru tools exec read_file --arg path="README.md"
        miru tools exec list_files --arg path="." --arg pattern="*.py"
        miru tools exec read_file --json '{"path": "README.md"}'
    """
    import json

    registry = _create_default_registry()

    try:
        tool = registry.get(name)
    except Exception:
        console.print(f"[red bold]✗[/] Tool not found: {name}")
        raise typer.Exit(1)

    arguments: dict = {}

    if json_input:
        try:
            arguments = json.loads(json_input)
        except json.JSONDecodeError as e:
            console.print(f"[red bold]✗[/] Invalid JSON: {e}")
            raise typer.Exit(1)
    else:
        for a in arg:
            if "=" not in a:
                console.print(f"[red bold]✗[/] Invalid argument format: {a}")
                console.print("[dim]Use KEY=VALUE format[/]")
                raise typer.Exit(1)
            key, value = a.split("=", 1)
            arguments[key] = value

    validation_errors = tool.validate_arguments(arguments)
    if validation_errors:
        console.print("[red bold]✗[/] Validation errors:")
        for error in validation_errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)

    console.print(f"[dim]Executing {name}...[/]\n")

    try:
        result = registry.execute(name, arguments)
        console.print("[green bold]✓ Result:[/]")
        if isinstance(result, str):
            if len(result) > 500:
                console.print(result[:500] + "...[dim](truncated)[/]")
            else:
                console.print(result)
        else:
            console.print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        console.print(f"[red bold]✗[/] Execution failed: {e}")
        raise typer.Exit(1)


@app.command("docs")
def tools_docs(
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Generate markdown documentation for all tools.

    Example:
        miru tools docs --output TOOLS.md
    """
    registry = _create_default_registry()
    tools = sorted(registry.list_tools(), key=lambda t: t.name)

    lines = [
        "# Tools Reference\n",
        "This document lists all available tools for function calling.\n",
        "## Overview\n\n",
        f"Total tools: {len(tools)}\n\n",
        "---\n\n",
    ]

    current_category = None
    for tool in tools:
        category = tool.name.split("_")[0] if "_" in tool.name else "general"
        if category != current_category:
            lines.append(f"\n## {category.title()} Tools\n\n")
            current_category = category

        lines.append(f"### `{tool.name}`\n\n")
        desc_lines = tool.description.strip().split("\n")
        lines.append(f"{desc_lines[0]}\n\n")

        if len(desc_lines) > 1:
            lines.append("**Details:**\n")
            for line in desc_lines[1:]:
                lines.append(f"- {line.strip()}\n")
            lines.append("\n")

        properties = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])

        if properties:
            lines.append("**Parameters:**\n\n")
            lines.append("| Name | Type | Required | Description |\n")
            lines.append("|------|------|----------|-------------|\n")
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "-")
                is_required = "✓" if param_name in required else ""
                lines.append(
                    f"| `{param_name}` | {param_type} | {is_required} | {param_desc} |\n"
                )
            lines.append("\n")

        lines.append("---\n\n")

    doc_content = "".join(lines)

    if output:
        from pathlib import Path

        Path(output).write_text(doc_content)
        console.print(f"[green bold]✓[/] Documentation written to {output}")
    else:
        console.print(doc_content)