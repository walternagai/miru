"""Tests for miru/commands/status.py — status, ps, stop, search commands."""

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
