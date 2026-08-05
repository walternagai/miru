"""Tests for miru/commands/run.py — _run_async success and error paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.run import _run_async


def _make_client(stream=False, models=None):
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.list_models = AsyncMock(return_value=models if models is not None else [{"name": "gemma3"}])

    async def gen():
        yield {"response": "resposta", "done": True, "eval_count": 3, "eval_duration": 1_000_000_000}

    client.generate = MagicMock(return_value=gen())
    client.chat = MagicMock(return_value=gen())
    return client


def _run(**kwargs):
    defaults = dict(
        model="gemma3", prompt="olá", host="http://x", system_prompt=None,
        images=[], files=[], audio=None, temperature=None, top_p=None,
        top_k=None, max_tokens=None, seed=None, repeat_penalty=None, ctx=None,
        no_stream=False, output_format="text", quiet=True, timeout=None,
        enable_tools=False, enable_tavily=False, sandbox_dir=None, tool_mode="auto_safe",
    )
    defaults.update(kwargs)
    return defaults


class TestRunAsync:
    def test_simple_generate(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run()))

    def test_no_stream_json(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(no_stream=True, output_format="json")))

    def test_quiet_text_stream(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(no_stream=False)))

    def test_system_prompt_chat(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(system_prompt="seja gentil")))

    def test_model_not_found(self) -> None:
        from miru.ollama.client import OllamaModelNotFound

        client = _make_client()
        client.generate = MagicMock(side_effect=OllamaModelNotFound("x"))
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run()))
        assert exc.value.code == 1

    def test_connection_error(self) -> None:
        from miru.ollama.client import OllamaConnectionError

        client = MagicMock()
        client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("down"))
        client.__aexit__ = AsyncMock(return_value=None)
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run()))
        assert exc.value.code == 1

    def test_vision_model_required(self) -> None:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.list_models = AsyncMock(return_value=[{"name": "gemma3"}])
        caps = MagicMock()
        caps.supports_vision = False
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.get_capabilities", new_callable=AsyncMock, return_value=caps):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(images=["foto.png"])))
        assert exc.value.code == 1

    def test_missing_file(self) -> None:
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(files=["nope.txt"])))
        assert exc.value.code == 1


class TestRunAsyncMore:
    def test_collect_chat_stream(self) -> None:
        from miru.commands.run import _collect_chat_stream

        async def gen():
            yield {"message": {"content": "parte1"}}
            yield {"message": {"content": "parte2"}, "done": True, "model": "gemma3"}

        text, final, model = asyncio.run(_collect_chat_stream(gen()))
        assert text == "parte1parte2"
        assert final is not None
        assert model == "gemma3"

    def test_ensure_model_already_available(self) -> None:
        from miru.commands.run import _ensure_model_available

        client = _make_client()
        with patch("miru.ollama.client.OllamaClient", return_value=client):
            asyncio.run(_ensure_model_available("gemma3", "http://x", quiet=True))

    def test_ensure_model_pulls_when_missing(self) -> None:
        from miru.commands.run import _ensure_model_available

        client = _make_client(models=[])
        # list_models vazio → tenta pull
        async def pull_gen():
            yield {"status": "success"}

        client.pull = MagicMock(return_value=pull_gen())
        with patch("miru.ollama.client.OllamaClient", return_value=client), \
             patch("miru.output.renderer.render_pull_progress", new_callable=AsyncMock) as mock_progress:
            asyncio.run(_ensure_model_available("novo", "http://x", quiet=True))
            assert client.pull.called

    def test_ensure_model_pull_failure(self) -> None:
        from miru.commands.run import _ensure_model_available
        from miru.ollama.client import OllamaConnectionError

        client = _make_client(models=[])
        async def pull_gen():
            raise OllamaConnectionError("down")
            yield  # pragma: no cover

        client.pull = MagicMock(return_value=pull_gen())
        with patch("miru.ollama.client.OllamaClient", return_value=client), \
             patch("miru.output.renderer.render_pull_progress", new_callable=AsyncMock):
            # não deve levantar
            asyncio.run(_ensure_model_available("novo", "http://x", quiet=True))

    def test_vision_flow_with_capabilities(self) -> None:
        """Modelo com visão → encode_images chamado, fluxo continua."""
        client = _make_client()
        caps = MagicMock()
        caps.supports_vision = True
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.get_capabilities", new_callable=AsyncMock, return_value=caps), \
             patch("miru.commands.run.encode_images", return_value=["b64"]) as mock_encode, \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(images=["foto.png"])))
            mock_encode.assert_called_once_with(["foto.png"])


class TestRunAsyncVisionBranches:
    def test_vision_no_vision_models_available(self) -> None:
        """Modelo sem visão e NENHUM modelo com visão → sugestão pull_vision_model."""
        client = _make_client()
        caps = MagicMock()
        caps.supports_vision = False
        # list_models retorna só o modelo sem visão
        client.list_models = AsyncMock(return_value=[{"name": "gemma3"}])

        # get_capabilities para o modelo consultado → False
        async def fake_caps(c, m):
            return caps

        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.get_capabilities", new=fake_caps):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(images=["foto.png"])))
        assert exc.value.code == 1

    def test_vision_with_vision_models(self) -> None:
        """Modelo sem visão mas há modelos com visão → sugestão com lista."""
        client = _make_client()
        caps = MagicMock()
        caps.supports_vision = False

        async def fake_caps(c, m):
            if m == "gemma3":
                return caps  # sem visão
            vision = MagicMock()
            vision.supports_vision = True
            return vision

        # list_models inclui um modelo com visão
        client.list_models = AsyncMock(return_value=[{"name": "gemma3"}, {"name": "llava:latest"}])

        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.get_capabilities", new=fake_caps):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(images=["foto.png"])))
        assert exc.value.code == 1

    def test_audio_transcription(self) -> None:
        """Áudio válido → transcrição adicionada ao contexto."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.transcribe", return_value="texto transcrito") as mock_tr, \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(audio="audio.mp3")))
            mock_tr.assert_called_once_with("audio.mp3")

    def test_audio_transcription_error(self) -> None:
        """Erro na transcrição → render_error + exit."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.transcribe", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(audio="audio.mp3")))
        assert exc.value.code == 1

    def test_file_processing_error(self) -> None:
        """Arquivo com erro de processamento → render_error + exit."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.extract_text", side_effect=RuntimeError("corrupt")):
            with pytest.raises(SystemExit) as exc:
                asyncio.run(_run_async(**_run(files=["x.pdf"])))
        assert exc.value.code == 1


class TestRunSystemPromptBranches:
    def test_system_prompt_non_quiet_text(self) -> None:
        """system_prompt + text + não-quiet + no_stream → render_markdown + metrics."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"), \
             patch("miru.commands.run.render_markdown") as mock_md, \
             patch("miru.commands.run.render_metrics") as mock_metrics:
            asyncio.run(_run_async(**_run(system_prompt="sys", no_stream=True, quiet=False)))
        assert mock_md.called

    def test_system_prompt_quiet_text(self) -> None:
        """system_prompt + text + quiet + no_stream → print direto."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"):
            asyncio.run(_run_async(**_run(system_prompt="sys", no_stream=True, quiet=True)))

    def test_system_prompt_streaming_live(self) -> None:
        """system_prompt + stream=True → stream_as_markdown_live."""
        client = _make_client()
        with patch("miru.commands.run.OllamaClient", return_value=client), \
             patch("miru.commands.run.record_history"), \
             patch("miru.commands.run.stream_as_markdown_live", new_callable=AsyncMock,
                   return_value=("resp", {"done": True})) as mock_live:
            asyncio.run(_run_async(**_run(system_prompt="sys", no_stream=False)))
        assert mock_live.called


class TestRunCliMore:
    def test_cli_auto_pull(self) -> None:
        """--auto-pull → _ensure_model_available chamado."""
        with patch("miru.commands.run._run_async", new_callable=AsyncMock) as mock_run, \
             patch("miru.commands.run._ensure_model_available", new_callable=AsyncMock) as mock_ensure:
            from typer.testing import CliRunner
            from miru.cli import app

            result = CliRunner().invoke(app, ["run", "gemma3", "olá", "--auto-pull", "--quiet"])
            assert result.exit_code == 0
            mock_ensure.assert_called_once()
