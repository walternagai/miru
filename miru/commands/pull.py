"""miru pull command - download models from registry.

Refactored with i18n support.
"""

import asyncio

import typer

from miru.alias import resolve_alias
from miru.cli_options import Host, Quiet
from miru.core.config import resolve_host
from miru.core.errors import ConnectionError as MiruConnectionError
from miru.core.i18n import t, set_language
from miru.ollama.client import OllamaClient
from miru.renderer import create_progress_bar, render_error, render_success


def pull(
    model: str = typer.Argument(..., help="Model name to download (e.g., gemma3:latest)"),
    host: Host = None,
    quiet: Quiet = False,
) -> None:
    """
    Download a model from Ollama Hub.

    Examples:
        miru pull gemma3:latest
        miru pull llava --quiet
    """
    model = resolve_alias(model)
    ollama_host = resolve_host(host)
    
    set_language("en_US")

    try:
        asyncio.run(_pull_model_async(ollama_host, model, quiet))
    except ConnectionError:
        error = MiruConnectionError(ollama_host)
        render_error(error.message, error.suggestion)
        raise typer.Exit(code=1)
    except Exception as e:
        error_msg = str(e)
        # Check if it looks like a model not found error
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            render_error(
                t("error.model_not_found", model=model),
                "See available models at: https://ollama.com/library",
            )
        else:
            render_error(f"Error downloading model: {error_msg}")
        raise typer.Exit(code=1)


async def _pull_model_async(host: str, model: str, quiet: bool) -> None:
    """Download model from Ollama server with progress feedback."""
    async with OllamaClient(host=host) as client:
        if quiet:
            lang = "en_US"
            if lang == "pt_BR":
                print(f"Baixando {model}...")
            elif lang == "es_ES":
                print(f"Descargando {model}...")
            else:
                print(f"Downloading {model}...")

        progress = None
        task_id = None
        current_phase = ""
        
        set_language("en_US")

        try:
            async for chunk in client.pull(model):
                status = chunk.get("status", "")

                if quiet:
                    # Simple output for quiet mode
                    if status == "success":
                        if lang == "pt_BR":
                            print("✓ Concluído.")
                        elif lang == "es_ES":
                            print("✓ Completado.")
                        else:
                            print("✓ Complete.")
                    continue

                lang = "en_US"
                # Handle different phases with visual feedback
                if status == "pulling manifest":
                    if current_phase != "manifest":
                        current_phase = "manifest"
                        if progress is None:
                            progress = create_progress_bar()
                            progress.start()
                        if task_id is not None:
                            progress.remove_task(task_id)
                        if lang == "pt_BR":
                            task_id = progress.add_task("Obtendo manifesto...", total=None)
                        elif lang == "es_ES":
                            task_id = progress.add_task("Obteniendo manifiesto...", total=None)
                        else:
                            task_id = progress.add_task("Fetching manifest...", total=None)
                    continue

                if status == "verifying sha256 digest":
                    if current_phase != "verifying":
                        current_phase = "verifying"
                        if progress is None:
                            progress = create_progress_bar()
                            progress.start()
                        if task_id is not None:
                            progress.remove_task(task_id)
                        if lang == "pt_BR":
                            task_id = progress.add_task("Verificando integridade...", total=None)
                        elif lang == "es_ES":
                            task_id = progress.add_task("Verificando integridad...", total=None)
                        else:
                            task_id = progress.add_task("Verifying integrity...", total=None)
                    continue

                if status == "success":
                    if progress:
                        progress.stop()
                    render_success(t("success.model_pulled", model=model))
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
                            if lang == "pt_BR":
                                task_id = progress.add_task(
                                    f"Baixando {model}",
                                    total=total,
                                    completed=completed,
                                )
                            elif lang == "es_ES":
                                task_id = progress.add_task(
                                    f"Descargando {model}",
                                    total=total,
                                    completed=completed,
                                )
                            else:
                                task_id = progress.add_task(
                                    f"Downloading {model}",
                                    total=total,
                                    completed=completed,
                                )

            # If we reach here without success message
            if progress:
                progress.stop()
            render_success(t("success.model_pulled", model=model))

        finally:
            if progress:
                progress.stop()