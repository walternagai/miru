"""miru embed command - generate embeddings."""

import asyncio
import json
import sys
from typing import Annotated

import typer

from miru.config import get_host
from miru.input import extract_text
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound


async def _embed_async(
    model: str,
    prompt: str,
    host: str,
    output_format: str,
    quiet: bool,
) -> None:
    """Async implementation of embed command."""
    async with OllamaClient(host) as client:
        try:
            result = await client.embed(model, prompt)

            embedding = result.get("embedding", [])

            if output_format == "json":
                output = {
                    "model": model,
                    "embedding": embedding,
                    "dimensions": len(embedding),
                }

                # Include timing if available
                if "total_duration" in result:
                    output["total_duration_ns"] = result["total_duration"]

                print(json.dumps(output, indent=2))
            elif output_format == "text":
                if quiet:
                    # Quiet mode: just print the embedding array
                    print(json.dumps(embedding))
                else:
                    print(f"Model: {model}")
                    print(f"Dimensions: {len(embedding)}")
                    if "total_duration" in result:
                        duration_ms = result["total_duration"] / 1e6
                        print(f"Duration: {duration_ms:.2f}ms")
                    print(f"\nEmbedding (first 10 values):")
                    print(json.dumps(embedding[:10], indent=2))
                    if len(embedding) > 10:
                        print(f"... ({len(embedding) - 10} more values)")

        except OllamaModelNotFound:
            from miru.renderer import render_error

            render_error(f'Modelo "{model}" não encontrado.', f"Para baixar: miru pull {model}")
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error

            render_error(str(e))
            sys.exit(1)


async def _embed_file_async(
    model: str,
    file_path: str,
    host: str,
    output_format: str,
    quiet: bool,
) -> None:
    """Embed content from file."""
    try:
        filename, content = extract_text(file_path)
    except FileNotFoundError as e:
        from miru.renderer import render_error

        render_error(str(e))
        sys.exit(1)
    except Exception as e:
        from miru.renderer import render_error

        render_error(str(e))
        sys.exit(1)

    await _embed_async(model, content, host, output_format, quiet)


async def _embed_batch_async(
    model: str,
    batch_file: str,
    host: str,
    output_format: str,
) -> None:
    """Embed multiple texts from a file (one per line or JSONL)."""
    from pathlib import Path

    path = Path(batch_file)
    if not path.exists():
        from miru.renderer import render_error

        render_error(f"Arquivo não encontrado: {batch_file}")
        sys.exit(1)

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        from miru.renderer import render_error

        render_error(f"Erro ao ler arquivo: {e}")
        sys.exit(1)

    lines = [line.strip() for line in content.split("\n") if line.strip()]

    if not lines:
        from miru.renderer import render_error

        render_error("Arquivo vazio ou sem linhas válidas")
        sys.exit(1)

    async with OllamaClient(host) as client:
        try:
            results = []

            for idx, line in enumerate(lines, start=1):
                # Try to parse as JSON if line starts with {
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        prompt = data.get("prompt", data.get("text", str(data)))
                    except json.JSONDecodeError:
                        prompt = line
                else:
                    prompt = line

                result = await client.embed(model, prompt)
                embedding = result.get("embedding", [])

                output = {
                    "line": idx,
                    "embedding": embedding,
                    "dimensions": len(embedding),
                }

                if "total_duration" in result:
                    output["duration_ms"] = result["total_duration"] / 1e6

                if output_format == "jsonl":
                    print(json.dumps(output))
                else:
                    results.append(output)

            if output_format == "json":
                print(json.dumps({"model": model, "results": results}, indent=2))

        except OllamaModelNotFound:
            from miru.renderer import render_error

            render_error(f'Modelo "{model}" não encontrado.', f"Para baixar: miru pull {model}")
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error

            render_error(str(e))
            sys.exit(1)


def embed(
    model: Annotated[str, typer.Argument(..., help="Model name (e.g., nomic-embed-text)")],
    text: Annotated[str | None, typer.Argument(help="Text to embed")] = None,
    file: Annotated[str | None, typer.Option("--file", "-f", help="File path to embed")] = None,
    batch: Annotated[
        str | None, typer.Option("--batch", "-b", help="Batch file (one text per line or JSONL)")
    ] = None,
    host: Annotated[str | None, typer.Option("--host", "-h", help="Ollama host URL")] = None,
    format: Annotated[
        str, typer.Option("--format", help="Output format (text/json/jsonl)")
    ] = "text",
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Minimal output (embedding array only)")
    ] = False,
) -> None:
    """Generate embedding vector for text.

    Examples:
        miru embed nomic-embed-text "Hello world"
        miru embed nomic-embed-text --file document.txt
        miru embed nomic-embed-text --batch texts.txt --format jsonl
    """
    if format not in ("text", "json", "jsonl"):
        from miru.renderer import render_error

        render_error(f"Invalid format: {format}. Use 'text', 'json', or 'jsonl'.")
        sys.exit(1)

    # Validate inputs
    provided_inputs = sum(1 for x in [text, file, batch] if x is not None)
    if provided_inputs == 0:
        from miru.renderer import render_error

        render_error(
            "Forneça um texto, arquivo (--file), ou batch (--batch).",
            "Exemplos:\n"
            '  miru embed nomic-embed-text "Hello world"\n'
            "  miru embed nomic-embed-text --file document.txt\n"
            "  miru embed nomic-embed-text --batch texts.txt",
        )
        sys.exit(1)

    if provided_inputs > 1:
        from miru.renderer import render_error

        render_error("Use apenas uma opção: texto, --file, ou --batch (não Combine).")
        sys.exit(1)

    resolved_host = get_host(host)

    try:
        if text is not None:
            asyncio.run(_embed_async(model, text, resolved_host, format, quiet))
        elif file is not None:
            if format == "jsonl":
                from miru.renderer import render_error

                render_error("--format jsonl é apenas para --batch. Use --format json para --file.")
                sys.exit(1)
            asyncio.run(_embed_file_async(model, file, resolved_host, format, quiet))
        elif batch is not None:
            asyncio.run(_embed_batch_async(model, batch, resolved_host, format))
    except KeyboardInterrupt:
        print()
        sys.exit(0)
