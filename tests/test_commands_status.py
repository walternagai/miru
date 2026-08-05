"""Tests for miru/commands/status.py — status, ps, stop, search commands."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from miru.cli import app
from typer.testing import CliRunner

runner = CliRunner()


class TestStatusCommand:
    @staticmethod
    def _mock_http_client(responses):
        """Build a mock httpx.AsyncClient context manager.

        responses: list of (status_code, json_value) — one per client.get call.
        """
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        results = []
        for code, value in responses:
            resp = MagicMock()
            resp.status_code = code
            resp.json.return_value = value
            results.append(resp)
        mock_client.get = AsyncMock(side_effect=results)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_http

    def test_connection_failed(self) -> None:
        with patch("httpx.AsyncClient", self._mock_http_client([(500, {})])):
            result = runner.invoke(app, ["status", "--host", "http://x:11434"])
            assert result.exit_code == 0

    def test_online_with_models(self) -> None:
        with patch("httpx.AsyncClient", self._mock_http_client([(200, {"ok": True})])), \
             patch("miru.commands.status.get_ollama_version", new_callable=AsyncMock) as mock_ver, \
             patch("miru.commands.status.get_running_models", new_callable=AsyncMock) as mock_ps:
            mock_ver.return_value = {"version": "0.5.0"}
            mock_ps.return_value = [{"name": "gemma3", "size": 100, "size_vram": 50, "expires": "x"}]
            result = runner.invoke(app, ["status", "--host", "http://x:11434"])
            assert result.exit_code == 0
            assert "gemma3" in result.output

    def test_no_models_message(self) -> None:
        with patch("httpx.AsyncClient", self._mock_http_client([(200, {"ok": True})])), \
             patch("miru.commands.status.get_ollama_version", new_callable=AsyncMock) as mock_ver, \
             patch("miru.commands.status.get_running_models", new_callable=AsyncMock) as mock_ps:
            mock_ver.return_value = {"version": "0.5.0"}
            mock_ps.return_value = []
            result = runner.invoke(app, ["status", "--host", "http://x:11434"])
            assert result.exit_code == 0


class TestPsCommand:
    def test_json_format(self) -> None:
        with patch("miru.commands.status.get_running_models", new_callable=AsyncMock) as mock_ps:
            mock_ps.return_value = [{"name": "llava", "size": 100}]
            result = runner.invoke(app, ["ps", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data[0]["name"] == "llava"

    def test_empty(self) -> None:
        with patch("miru.commands.status.get_running_models", new_callable=AsyncMock) as mock_ps:
            mock_ps.return_value = []
            result = runner.invoke(app, ["ps"])
            assert result.exit_code == 0

    def test_text_format(self) -> None:
        with patch("miru.commands.status.get_running_models", new_callable=AsyncMock) as mock_ps:
            mock_ps.return_value = [{"name": "gemma3", "size": 1024}]
            result = runner.invoke(app, ["ps"])
            assert result.exit_code == 0
            assert "gemma3" in result.output


class TestStopCommand:
    def test_stop_success(self) -> None:
        with patch("miru.commands.status._stop_model_async", new_callable=AsyncMock) as mock_stop:
            result = runner.invoke(app, ["stop", "gemma3"])
            assert result.exit_code == 0
            mock_stop.assert_called_once()

    def test_stop_error(self) -> None:
        with patch("miru.commands.status._stop_model_async", new_callable=AsyncMock) as mock_stop:
            mock_stop.side_effect = RuntimeError("failed")
            result = runner.invoke(app, ["stop", "gemma3"])
            assert result.exit_code == 0  # error is printed, not raised


class TestSearchCommand:
    def test_json_no_results(self) -> None:
        with patch("miru.commands.status._search_async", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = runner.invoke(app, ["search", "nonexistent", "--format", "json"])
            assert result.exit_code == 0
            assert json.loads(result.output) == []

    def test_text_no_results(self) -> None:
        with patch("miru.commands.status._search_async", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            result = runner.invoke(app, ["search", "zzz"])
            assert result.exit_code == 0

    def test_text_with_results(self) -> None:
        with patch("miru.commands.status._search_async", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {"name": "gemma3:latest", "size": 100, "modified_at": "2026-04-01T00:00:00"}
            ]
            result = runner.invoke(app, ["search", "gemma"])
            assert result.exit_code == 0
            assert "gemma3:latest" in result.output


class TestStatusHelpers:
    @pytest.mark.asyncio
    async def test_get_ollama_version_success(self) -> None:
        from unittest.mock import MagicMock
        from miru.commands.status import get_ollama_version

        mock_client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"version": "0.5.0"}
        mock_client.get = AsyncMock(return_value=resp)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            result = await get_ollama_version("http://x:11434")
        assert result == {"version": "0.5.0"}

    @pytest.mark.asyncio
    async def test_get_ollama_version_failure(self) -> None:
        from unittest.mock import MagicMock
        from miru.commands.status import get_ollama_version

        mock_client = MagicMock()
        resp = MagicMock()
        resp.status_code = 500
        mock_client.get = AsyncMock(return_value=resp)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            result = await get_ollama_version("http://x:11434")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_running_models(self) -> None:
        from unittest.mock import MagicMock
        from miru.commands.status import get_running_models

        mock_client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"models": [{"name": "gemma3"}]}
        mock_client.get = AsyncMock(return_value=resp)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            models = await get_running_models("http://x:11434")
        assert models == [{"name": "gemma3"}]

    @pytest.mark.asyncio
    async def test_get_running_models_empty(self) -> None:
        from unittest.mock import MagicMock
        from miru.commands.status import get_running_models

        mock_client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"models": []}
        mock_client.get = AsyncMock(return_value=resp)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            models = await get_running_models("http://x:11434")
        assert models == []


class TestStatusErrorBranches:
    @pytest.mark.asyncio
    async def test_connect_error_branch(self) -> None:
        """httpx.ConnectError → mensagem de conexão."""
        from unittest.mock import MagicMock

        import httpx
        from miru.commands.status import _status_async

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("conn refused"))
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            await _status_async("http://x:11434", verbose=False)

    @pytest.mark.asyncio
    async def test_timeout_error_branch(self) -> None:
        """httpx.TimeoutException → mensagem de timeout."""
        from unittest.mock import MagicMock

        import httpx
        from miru.commands.status import _status_async

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            await _status_async("http://x:11434", verbose=False)

    @pytest.mark.asyncio
    async def test_unexpected_error_branch(self) -> None:
        """Erro genérico → mensagem de erro inesperado."""
        from unittest.mock import MagicMock

        from miru.commands.status import _status_async

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("boom"))
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            await _status_async("http://x:11434", verbose=False)

    @pytest.mark.asyncio
    async def test_stop_model_error(self) -> None:
        """_stop_model_async com erro → re-raise com mensagem."""
        from unittest.mock import MagicMock

        import httpx
        from miru.commands.status import _stop_model_async

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            with pytest.raises(Exception) as exc:
                await _stop_model_async("http://x:11434", "gemma3", -1)
            assert "Error stopping model" in str(exc.value)


class TestSearchAsync:
    @pytest.mark.asyncio
    async def test_search_filters_by_name(self) -> None:
        from unittest.mock import MagicMock

        from miru.commands.status import _search_async

        mock_client = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"models": [{"name": "gemma3:latest"}, {"name": "llama3"}]}
        mock_client.get = AsyncMock(return_value=resp)
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            models = await _search_async("http://x:11434", "gemma")
        assert models == [{"name": "gemma3:latest"}]

    @pytest.mark.asyncio
    async def test_search_error_returns_empty(self) -> None:
        from unittest.mock import MagicMock

        import httpx
        from miru.commands.status import _search_async

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        mock_http = MagicMock()
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch("httpx.AsyncClient", mock_http):
            models = await _search_async("http://x:11434", "gemma")
        assert models == []
