"""Status command for Ollama health check."""

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from miru.config_manager import resolve_host

console = Console()


async def get_ollama_version(host: str) -> dict | None:
    """Get Ollama version info."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/version")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


async def get_running_models(host: str) -> list[dict]:
    """Get currently running/loaded models."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/ps")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
    except Exception:
        pass
    return []


async def _status_async(host: str, verbose: bool) -> None:
    """Async status check."""
    import httpx

    version_info = None
    running_models = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            check_response = await client.get(f"{host}/")
            if check_response.status_code != 200:
                console.print(f"[red bold]✗[/] Ollama não está respondendo em {host}")
                console.print("[dim]Verifique se o Ollama está rodando: ollama serve[/]")
                return

            version_info = await get_ollama_version(host)

            running_models = await get_running_models(host)

        console.print(f"[green bold]✓[/] Ollama está acessível em {host}")
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Propriedade", style="dim")
        table.add_column("Valor")

        table.add_row("Host", host)
        table.add_row("Status", "[green]Online[/]")
        table.add_row(
            "Versão", version_info.get("version", "unknown") if version_info else "unknown"
        )

        if running_models:
            console.print()
            console.print(f"[bold]Modelos carregados na VRAM ({len(running_models)}):[/]")
            models_table = Table(show_header=True, header_style="bold cyan")
            models_table.add_column("Modelo", style="green")
            models_table.add_column("Tamanho", justify="right")
            models_table.add_column("VRAM", justify="right")
            models_table.add_column("Expira em", justify="right")

            for m in running_models:
                from miru.output.renderer import format_size

                name = m.get("name", "-")
                size = format_size(m.get("size", 0))
                vram = format_size(m.get("size_vram", 0)) if m.get("size_vram") else "—"
                expires = m.get("expires", "-")

                models_table.add_row(name, size, vram, str(expires))

            console.print(models_table)
        else:
            console.print()
            console.print("[dim]Nenhum modelo carregado na VRAM[/]")

    except httpx.ConnectError:
        console.print(f"[red bold]✗[/] Cannot connect to Ollama at {host}")
        console.print("[dim]Verifique se o Ollama está rodando: ollama serve[/]")
    except httpx.TimeoutException:
        console.print(f"[red bold]✗[/] Timeout connecting to Ollama at {host}")
    except Exception as e:
        console.print(f"[red bold]✗[/] Error: {e}")


def status(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed info")] = False,
) -> None:
    """Check Ollama server status and running models.

    Examples:
        miru status
        miru status --verbose
    """
    resolved_host = resolve_host(host)
    asyncio.run(_status_async(resolved_host, verbose))


async def _ps_async(host: str) -> list[dict]:
    """Async get running models."""
    return await get_running_models(host)


def ps(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (text/json)")
    ] = "text",
) -> None:
    """List models currently loaded in VRAM.

    Examples:
        miru ps
        miru ps --format json
    """
    import json

    resolved_host = resolve_host(host)
    models = asyncio.run(_ps_async(resolved_host))

    if format == "json":
        print(json.dumps(models, indent=2))
        return

    if not models:
        console.print("[dim]Nenhum modelo carregado na VRAM[/]")
        return

    from miru.output.renderer import format_size

    table = Table(title="Modelos na VRAM", show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Tamanho", justify="right")
    table.add_column("VRAM", justify="right")
    table.add_column("Expira em", justify="right")

    for m in models:
        name = m.get("name", "-")
        size = format_size(m.get("size", 0))
        vram = format_size(m.get("size_vram", 0)) if m.get("size_vram") else "—"
        expires = m.get("expires", "-")

        table.add_row(name, size, vram, str(expires))

    console.print(table)


async def _stop_model_async(host: str, model: str, keep_alive_minutes: int) -> None:
    """Stop/unload a model from VRAM."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{host}/api/generate",
                json={"model": model, "keep_alive": keep_alive_minutes},
            )
    except Exception as e:
        raise Exception(f"Error stopping model: {e}")


def stop(
    model: Annotated[str, typer.Argument(help="Model name to stop")],
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force immediate unload")] = False,
) -> None:
    """Unload a model from VRAM.

    Examples:
        miru stop gemma3:latest
        miru stop llava:latest --force
    """
    resolved_host = resolve_host(host)
    keep_alive = 0 if force else -1

    try:
        asyncio.run(_stop_model_async(resolved_host, model, keep_alive))
        console.print(f"[green bold]✓[/] Model {model} unloaded")
    except Exception as e:
        console.print(f"[red bold]✗[/] {e}")


async def _search_async(host: str, query: str) -> list[dict]:
    """Search for models in registry (limited functionality)."""
    import httpx

    models = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{host}/api/tags")
            if response.status_code == 200:
                data = response.json()
                all_models = data.get("models", [])

                query_lower = query.lower()
                for m in all_models:
                    name = m.get("name", "")
                    if query_lower in name.lower():
                        models.append(m)
    except Exception:
        pass

    return models


def search(
    query: Annotated[str, typer.Argument(help="Search query (model name filter)")],
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (text/json)")
    ] = "text",
) -> None:
    """Search for models locally (filter by name).

    Examples:
        miru search gemma
        miru search llama --format json
    """
    import json

    resolved_host = resolve_host(host)
    models = asyncio.run(_search_async(resolved_host, query))

    if format == "json":
        print(json.dumps(models, indent=2))
        return

    if not models:
        console.print(f"[dim]Nenhum modelo encontrado para '{query}'[/]")
        return

    from miru.output.renderer import format_size, format_date

    table = Table(title=f"Modelos matching '{query}'", show_header=True, header_style="bold cyan")
    table.add_column("Modelo", style="green")
    table.add_column("Tamanho", justify="right")
    table.add_column("Modificado", justify="center")

    for m in models:
        name = m.get("name", "-")
        size = format_size(m.get("size", 0))
        modified = format_date(m.get("modified_at", ""))

        table.add_row(name, size, modified)

    console.print(table)
