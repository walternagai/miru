"""Tests for miru/commands/pull.py — pull progress and error paths."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miru.commands.pull import _pull_model_async


def _make_client():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    async def gen():
        yield {"status": "pulling manifest"}
        yield {"status": "downloading", "completed": 10, "total": 100}
        yield {"status": "success"}

    client.pull = MagicMock(return_value=gen())
    return client


class TestPullAsync:
    def test_quiet_success(self) -> None:
        client = _make_client()
        with patch("miru.commands.pull.OllamaClient", return_value=client):
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=True))

    def test_non_quiet_success(self) -> None:
        client = _make_client()
        with patch("miru.commands.pull.OllamaClient", return_value=client), \
             patch("miru.commands.pull.create_progress_bar") as mock_bar:
            progress = MagicMock()
            mock_bar.return_value = progress
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=False))
            assert progress.stop.called or progress.start.called

    def test_connection_error_from_pull(self) -> None:
        from miru.ollama.client import OllamaConnectionError

        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            raise OllamaConnectionError("down")
            yield  # pragma: no cover

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client):
            with pytest.raises(OllamaConnectionError):
                asyncio.run(_pull_model_async("http://x", "gemma3", quiet=True))


class TestPullPhases:
    def test_non_quiet_all_phases(self) -> None:
        """Cobre pulling manifest, downloading (com progress), verifying e success."""
        from miru.core.i18n import set_language

        set_language("pt_BR")
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            yield {"status": "pulling manifest"}
            yield {"status": "downloading", "completed": 10, "total": 100}
            yield {"status": "verifying sha256 digest"}
            yield {"status": "success"}

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client), \
             patch("miru.commands.pull.create_progress_bar") as mock_bar:
            progress = MagicMock()
            mock_bar.return_value = progress
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=False))
        set_language("en_US")

    def test_es_lang_quiet(self) -> None:
        from miru.core.i18n import set_language

        set_language("es_ES")
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            yield {"status": "downloading", "completed": 1, "total": 2}
            yield {"status": "success"}

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client):
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=True))
        set_language("en_US")


class TestPullEsBranches:
    def test_es_manifest_and_verify(self) -> None:
        """Fases manifest/verifying com lang es_ES."""
        from miru.core.i18n import set_language

        set_language("es_ES")
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            yield {"status": "pulling manifest"}
            yield {"status": "verifying sha256 digest"}
            yield {"status": "success"}

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client), \
             patch("miru.commands.pull.create_progress_bar") as mock_bar:
            progress = MagicMock()
            mock_bar.return_value = progress
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=False))
        set_language("en_US")

    def test_en_quiet_complete(self) -> None:
        from miru.core.i18n import set_language

        set_language("en_US")
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            yield {"status": "success"}

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client):
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=True))
        set_language("en_US")


class TestPullDownloadingEs:
    def test_downloading_es_lang(self) -> None:
        """download com lang es_ES → label Descargando."""
        from miru.core.i18n import set_language

        set_language("es_ES")
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        async def gen():
            yield {"status": "downloading", "completed": 10, "total": 100}
            yield {"status": "success"}

        client.pull = MagicMock(return_value=gen())
        with patch("miru.commands.pull.OllamaClient", return_value=client), \
             patch("miru.commands.pull.create_progress_bar") as mock_bar:
            progress = MagicMock()
            mock_bar.return_value = progress
            asyncio.run(_pull_model_async("http://x", "gemma3", quiet=False))
        set_language("en_US")
