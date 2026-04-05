"""miru pull command - download models."""

import asyncio
from typing import Optional

import typer

from miru.config import get_host
from miru.ollama.client import OllamaClient, OllamaConnectionError
from miru.renderer import (
    create_progress_bar,
    render_error,
    render_success,
)


def pull(
    model: str = typer.Argument(..., help="Model name to download (e.g., gemma3:latest)"),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        "-h",
        help="Ollama host URL (default: http://localhost:11434)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimal output for scripts",
    ),
) -> None:
    """
    Download a model from Ollama Hub.

    Examples:
        miru pull gemma3:latest
        miru pull llava --quiet
    """
    ollama_host = get_host(host)

    try:
        asyncio.run(_pull_model_async(ollama_host, model, quiet))
    except OllamaConnectionError:
        render_error(
            f"Não foi possível conectar ao Ollama em {ollama_host}",
            "Verifique se o Ollama está rodando: ollama serve",
        )
        raise typer.Exit(code=1)
    except Exception as e:
        error_msg = str(e)
        # Check if it looks like a model not found error
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            render_error(
                f'Modelo "{model}" não encontrado no Ollama Hub.',
                "Veja modelos disponíveis em: https://ollama.com/library",
            )
        else:
            render_error(f"Erro ao baixar modelo: {error_msg}")
        raise typer.Exit(code=1)


async def _pull_model_async(host: str, model: str, quiet: bool) -> None:
    """Download model from Ollama server with progress feedback."""
    async with OllamaClient(host=host) as client:
        if quiet:
            print(f"Baixando {model}...")

        progress = None
        task_id = None
        current_phase = ""

        try:
            async for chunk in client.pull(model):
                status = chunk.get("status", "")

                if quiet:
                    # Simple output for quiet mode
                    if status == "success":
                        print("✓ Concluído.")
                    continue

                # Handle different phases with visual feedback
                if status == "pulling manifest":
                    if current_phase != "manifest":
                        current_phase = "manifest"
                        if progress is None:
                            progress = create_progress_bar()
                            progress.start()
                        if task_id is not None:
                            progress.remove_task(task_id)
                        task_id = progress.add_task("Obtendo manifesto...", total=None)
                    continue

                if status == "verifying sha256 digest":
                    if current_phase != "verifying":
                        current_phase = "verifying"
                        if progress is None:
                            progress = create_progress_bar()
                            progress.start()
                        if task_id is not None:
                            progress.remove_task(task_id)
                        task_id = progress.add_task("Verificando integridade...", total=None)
                    continue

                if status == "success":
                    if progress:
                        progress.stop()
                    render_success(f"{model} baixado com sucesso.")
                    return

                if status == "downloading":
                    current_phase = "downloading"
                    total = chunk.get("total")
                    completed = chunk.get("completed", 0)

                    if total:
                        if progress is None:
                            progress = create_progress_bar()
                            progress.start()

                        if task_id is not None:
                            progress.update(task_id, completed=completed, total=total)
                        else:
                            task_id = progress.add_task(
                                f"Baixando {model}",
                                total=total,
                                completed=completed,
                            )

            # If we reach here without success message
            if progress:
                progress.stop()
            render_success(f"{model} baixado com sucesso.")

        finally:
            if progress:
                progress.stop()