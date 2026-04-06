"""Chat command for multi-turn interactive inference."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from miru.alias import resolve_alias
from miru.config import get_host
from miru.config_manager import load_config
from miru.history import record_history
from miru.inference_params import build_options
from miru.ollama.client import OllamaClient, OllamaConnectionError, OllamaModelNotFound

console = Console()


def _print_help() -> None:
    """Print chat commands help."""
    console.print()
    console.print("[bold]Comandos do Chat:[/]")
    console.print("  /exit, /quit   - Encerrar sessão")
    console.print("  /clear         - Limpar histórico")
    console.print("  /history       - Mostrar contagem de turnos")
    console.print("  /stats         - Mostrar métricas da sessão")
    console.print("  /model <name>  - Trocar modelo")
    console.print("  /system <p>    - Alterar system prompt")
    console.print("  /retry         - Re-executar último prompt")
    console.print("  /save <file>   - Salvar conversa")
    console.print("  /help          - Mostrar esta ajuda")
    console.print()


async def _chat_async(
    model: str,
    host: str,
    system_prompt: str | None,
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
    model = resolve_alias(model)

    async with OllamaClient(host) as client:
        try:
            all_models = await client.list_models()
            model_names = [m.get("name", "") for m in all_models]
            if model not in model_names:
                from miru.renderer import render_error

                render_error(f'Modelo "{model}" não encontrado.', f"Para baixar: miru pull {model}")
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
                if system_prompt:
                    print(f"System: {system_prompt[:50]}{'...' if len(system_prompt) > 50 else ''}")
                print("Digite /help para ver comandos disponíveis")
                print("─" * 50)

            messages: list[dict[str, str]] = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            turn_count = 0
            total_tokens = 0
            total_time_ns = 0
            last_user_input: str | None = None
            current_model = model
            current_system = system_prompt

            while True:
                try:
                    user_input = input(">>> ")
                except EOFError:
                    break
                except KeyboardInterrupt:
                    if not quiet:
                        print()
                        print("─" * 50)
                        print(f"Sessão encerrada · {turn_count} turn(s) · {current_model}")
                        if total_tokens > 0 and total_time_ns > 0:
                            avg_speed = total_tokens / (total_time_ns / 1e9)
                            print(
                                f"Total: {total_tokens} tokens · Velocidade média: {avg_speed:.1f} tok/s"
                            )
                    sys.exit(0)

                if not user_input.strip():
                    continue

                stripped = user_input.strip()

                if stripped in ("/exit", "/quit"):
                    if not quiet:
                        print("─" * 50)
                        print(f"Sessão encerrada · {turn_count} turn(s) · {current_model}")
                        if total_tokens > 0 and total_time_ns > 0:
                            avg_speed = total_tokens / (total_time_ns / 1e9)
                            print(
                                f"Total: {total_tokens} tokens · Velocidade média: {avg_speed:.1f} tok/s"
                            )
                    break

                if stripped == "/clear":
                    messages = []
                    if current_system:
                        messages.append({"role": "system", "content": current_system})
                    turn_count = 0
                    total_tokens = 0
                    total_time_ns = 0
                    if not quiet:
                        console.print("[green]✓[/] Histórico limpo.")
                    continue

                if stripped == "/history":
                    if not quiet:
                        print(f"Turn(s): {turn_count}")
                    continue

                if stripped == "/help":
                    _print_help()
                    continue

                if stripped == "/stats":
                    if not quiet:
                        console.print("[bold]Estatísticas da Sessão[/]")
                        console.print(f"  Modelo: {current_model}")
                        console.print(f"  Turnos: {turn_count}")
                        console.print(f"  Tokens: {total_tokens}")
                        if total_time_ns > 0:
                            total_seconds = total_time_ns / 1e9
                            console.print(f"  Tempo: {total_seconds:.1f}s")
                            avg_speed = total_tokens / total_seconds
                            console.print(f"  Velocidade média: {avg_speed:.1f} tok/s")
                        if current_system:
                            console.print(f"  System prompt: {current_system[:50]}...")
                    continue

                if stripped.startswith("/model "):
                    new_model = stripped[7:].strip()
                    new_model = resolve_alias(new_model)

                    if new_model not in model_names:
                        console.print(f"[red bold]✗[/] Modelo '{new_model}' não encontrado")
                        console.print("[dim]Modelos disponíveis: miru list[/]")
                        continue

                    current_model = new_model
                    console.print(f"[green]✓[/] Modelo alterado para: {current_model}")
                    continue

                if stripped.startswith("/system "):
                    new_system = stripped[8:].strip()
                    current_system = new_system
                    messages = [{"role": "system", "content": new_system}] + [
                        m for m in messages if m.get("role") != "system"
                    ]
                    console.print("[green]✓[/] System prompt atualizado")
                    continue

                if stripped == "/retry":
                    if last_user_input is None:
                        console.print("[yellow]Nenhum prompt anterior para repetir[/]")
                        continue
                    user_input = last_user_input
                else:
                    last_user_input = user_input

                if stripped.startswith("/save "):
                    filename = stripped[6:].strip()
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(f"# Chat session with {current_model}\n\n")
                            for m in messages:
                                role = m.get("role", "unknown")
                                content = m.get("content", "")
                                f.write(f"## {role.upper()}\n{content}\n\n")
                            f.write(
                                f"## Session Stats\n- Turns: {turn_count}\n- Tokens: {total_tokens}\n"
                            )
                        console.print(f"[green]✓[/] Conversa salva em: {filename}")
                    except Exception as e:
                        console.print(f"[red bold]✗[/] Erro ao salvar: {e}")
                    continue

                messages.append({"role": "user", "content": user_input})

                response_parts = []
                final_chunk = None

                chunks = client.chat(current_model, messages, options=options, stream=True)
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

                    duration_ns = eval_duration_ns if eval_duration_ns > 0 else total_duration_ns
                    duration_seconds = duration_ns / 1e9

                    if duration_seconds > 0 and eval_count > 0:
                        tokens_per_second = eval_count / duration_seconds
                        print(f"[{eval_count} tok · {tokens_per_second:.1f} tok/s]")
                    else:
                        print(f"[{eval_count} tok]")
                    print()

                    total_tokens += eval_count
                    total_time_ns += duration_ns

                response_text = "".join(response_parts)
                messages.append({"role": "assistant", "content": response_text})
                turn_count += 1

                record_history(
                    command="chat",
                    model=current_model,
                    prompt=user_input,
                    system_prompt=current_system,
                    response=response_text[:1000],
                    success=True,
                    metrics={"eval_count": final_chunk.get("eval_count", 0) if final_chunk else 0},
                )

        except OllamaModelNotFound:
            from miru.renderer import render_error

            render_error(f'Modelo "{model}" não encontrado.', f"Para baixar: miru pull {model}")
            sys.exit(1)
        except OllamaConnectionError as e:
            from miru.renderer import render_error

            render_error(str(e))
            sys.exit(1)


def chat(
    model: Annotated[str | None, typer.Argument(help="Model name")] = None,
    system: Annotated[
        str | None, typer.Option("--system", "-s", help="System prompt to set model behavior")
    ] = None,
    system_file: Annotated[
        str | None, typer.Option("--system-file", help="Read system prompt from file")
    ] = None,
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
    """Start interactive chat session.

    Chat commands:
        /exit, /quit   - End session
        /clear         - Clear history
        /history       - Show turn count
        /stats         - Show session statistics
        /model <name>  - Switch model
        /system <p>    - Change system prompt
        /retry         - Retry last prompt
        /save <file>   - Save conversation
        /help          - Show commands

    Examples:
        miru chat gemma3:latest
        miru chat --system "You are a helpful assistant"
        miru chat qwen2.5:7b --system-file prompt.txt
    """
    config = load_config()

    if model is None:
        model = config.default_model
        if model is None:
            console.print("[red bold]✗[/] Model não especificado")
            console.print("[dim]Use: miru chat <model>[/]")
            console.print(
                "[dim]Ou configure default_model: miru config set default_model gemma3:latest[/]"
            )
            sys.exit(1)

    model = resolve_alias(model)

    if system is not None and system_file is not None:
        from miru.renderer import render_error

        render_error("Use --system OU --system-file, não ambos.")
        sys.exit(1)

    final_system_prompt: str | None = None
    if system_file is not None:
        try:
            system_path = Path(system_file)
            if not system_path.exists():
                from miru.renderer import render_error

                render_error(f"Arquivo não encontrado: {system_file}")
                sys.exit(1)
            final_system_prompt = system_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            from miru.renderer import render_error

            render_error(f"Erro ao ler arquivo de system prompt: {e}")
            sys.exit(1)
    elif system is not None:
        final_system_prompt = system.strip()

    resolved_host = get_host(host)

    try:
        asyncio.run(
            _chat_async(
                model=model,
                host=resolved_host,
                system_prompt=final_system_prompt,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                seed=seed,
                repeat_penalty=repeat_penalty,
                ctx=ctx,
                quiet=quiet,
            )
        )
    except KeyboardInterrupt:
        sys.exit(0)
