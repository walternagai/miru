"""Tests for miru/commands/setup.py — setup wizard (non-interactive paths)."""

from unittest.mock import AsyncMock, patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestSetup:
    def test_non_interactive_ollama_down(self) -> None:
        with patch("miru.commands.setup.check_ollama", new_callable=AsyncMock) as mock_check, \
             patch("miru.commands.setup.get_models", new_callable=AsyncMock) as mock_models:
            mock_check.return_value = (False, "")
            mock_models.return_value = []
            result = runner.invoke(app, ["setup", "--non-interactive", "--host", "http://x:11434"])
            assert result.exit_code == 0

    def test_non_interactive_full_flow(self, tmp_path, monkeypatch) -> None:
        import miru.commands.setup as setup_mod
        from miru.core.config import Config

        cfg = Config()
        monkeypatch.setattr(setup_mod, "load_config", lambda: cfg)
        monkeypatch.setattr(setup_mod, "save_config", lambda c: None)

        with patch("miru.commands.setup.check_ollama", new_callable=AsyncMock) as mock_check, \
             patch("miru.commands.setup.get_models", new_callable=AsyncMock) as mock_models:
            mock_check.return_value = (True, "0.5.0")
            mock_models.return_value = ["gemma3:latest", "llama3"]
            result = runner.invoke(app, ["setup", "--non-interactive", "--host", "http://x:11434"])
            assert result.exit_code == 0
            assert cfg.default_model == "gemma3:latest"
            assert cfg.default_host == "http://x:11434"

    def test_check_ollama_returns_version(self) -> None:
        from unittest.mock import MagicMock

        import asyncio
        from miru.commands.setup import check_ollama

        async def run():
            mock_client = MagicMock()
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"version": "0.9.0"}
            mock_client.get = AsyncMock(return_value=resp)
            mock_http = MagicMock()
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch("httpx.AsyncClient", mock_http):
                return await check_ollama("http://x:11434")

        ok, version = asyncio.run(run())
        assert ok is True
        assert version == "0.9.0"

    def test_check_ollama_failure(self) -> None:
        from unittest.mock import MagicMock

        import asyncio
        from miru.commands.setup import check_ollama

        async def run():
            mock_http = MagicMock()
            mock_client = MagicMock()
            mock_client.get = AsyncMock(side_effect=RuntimeError("down"))
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
            with patch("httpx.AsyncClient", mock_http):
                return await check_ollama("http://x:11434")

        ok, version = asyncio.run(run())
        assert ok is False
        assert version == ""

    def test_get_models(self) -> None:
        import asyncio
        from miru.commands.setup import get_models

        async def run():
            mock_client = AsyncMock()
            mock_client.list_models = AsyncMock(return_value=[{"name": "a"}, {"name": "b"}])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            with patch("miru.commands.setup.OllamaClient", return_value=mock_client):
                return await get_models("http://x:11434")

        models = asyncio.run(run())
        assert models == ["a", "b"]

    def test_get_models_error_returns_empty(self) -> None:
        import asyncio
        from miru.commands.setup import get_models

        async def run():
            with patch("miru.commands.setup.OllamaClient", side_effect=RuntimeError("boom")):
                return await get_models("http://x:11434")

        assert asyncio.run(run()) == []
