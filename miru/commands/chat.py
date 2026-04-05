"""Chat command for multi-turn interactive inference."""

import asyncio
import sys
from typing import Annotated

import typer

from miru.config import get_host
from miru.inference_params import build_options
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound


async def _chat_async(
    model: str,
    host: str,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    max_tokens: int | None,
    seed: int | None,
    repeat_penalty: float | None,
    ctx: int | None,
    quiet: bool,
) -> None:
    """Async implementation of chat command."""
    async with OllamaClient(host) as client:
        try:
            all_models = await client.list_models()
            model_names = [m.get("name", "") for m in all_models]
            if model not in model_names:
                from miru.renderer import render_error
                render_error(
                    f'Modelo "{model}" não encontrado.',
                    f"Para baixar: miru pull {model}"
                )
                sys.exit(1)

            options = build_options(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
            )

            if not quiet:
                print(f"miru chat · {model}")
                print("Digite /exit para sair · /clear para novo contexto")
                print("─" * 50)

            messages: list[dict[str, str]] = []
            turn_count = 0

            while True:
                try:
                    user_input = input(">>> ")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    if not quiet:
                        print()
                        print("─" * 50)
                        print(f"Sessão encerrada · {turn_count} turn(s) · {model}")
                    sys.exit(0)

                if not user_input.strip():
                    continue

                if user_input.strip() in ("/exit", "/quit"):
                    if not quiet:
                        print("─" * 50)
                        print(f"Sessão encerrada · {turn_count} turn(s) · {model}")
                    break

                if user_input.strip() == "/clear":
                    messages = []
                    turn_count = 0
                    if not quiet:
                        print("Histórico limpo.")
                    continue

                if user_input.strip() == "/history":
                    if not quiet:
                        print(f"Turn(s): {turn_count}")
                    continue

                messages.append({"role": "user", "content": user_input})

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
                    total_duration_ns = final_chunk.get("total_duration", 0)

                    eval_seconds = eval_duration_ns / 1e9
                    tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0

                    print(f"[{eval_count} tok · {tokens_per_second:.1f} tok/s]")
                    print()

                response_text = "".join(response_parts)
                messages.append({"role": "assistant", "content": response_text})
                turn_count += 1

        except OllamaModelNotFound:
            from miru.renderer import render_error
            render_error(
                f'Modelo "{model}" não encontrado.',
                f"Para baixar: miru pull {model}"
            )
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error
            render_error(str(e))
            sys.exit(1)


def chat(
    model: str,
    temperature: Annotated[float | None, typer.Option(help="Sampling temperature")] = None,
    top_p: Annotated[float | None, typer.Option(help="Nucleus sampling probability")] = None,
    top_k: Annotated[int | None, typer.Option(help="Top-k sampling")] = None,
    max_tokens: Annotated[int | None, typer.Option(help="Max tokens to generate")] = None,
    seed: Annotated[int | None, typer.Option(help="Random seed")] = None,
    repeat_penalty: Annotated[float | None, typer.Option(help="Repetition penalty")] = None,
    ctx: Annotated[int | None, typer.Option(help="Context window size")] = None,
    host: Annotated[str | None, typer.Option(help="Ollama host URL")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Minimal output")] = False,
) -> None:
    """Start interactive chat session."""
    resolved_host = get_host(host)

    try:
        asyncio.run(_chat_async(
            model=model,
            host=resolved_host,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
            seed=seed,
            repeat_penalty=repeat_penalty,
            ctx=ctx,
            quiet=quiet,
        ))
    except KeyboardInterrupt:
        sys.exit(0)