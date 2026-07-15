"""Tests for miru/commands/embed.py."""

import json
from unittest.mock import AsyncMock, patch
from pathlib import Path
import tempfile

import pytest
from typer.testing import CliRunner

from miru.cli import app
from miru.ollama.client import OllamaConnectionError, OllamaModelNotFound

runner = CliRunner()


class TestEmbedCommand:
    """Tests for miru embed command."""

    def test_embed_text_basic(self) -> None:
        """Should embed single text."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.embed = AsyncMock(
                return_value={
                    "embedding": [0.1, 0.2, 0.3],
                    "total_duration": 1000000,
                }
            )
            MockClient.return_value = client

            result = runner.invoke(
                app, ["embed", "nomic-embed-text", "Hello world", "--format", "text"]
            )

            assert result.exit_code == 0
            assert "nomic-embed-text" in result.output
            assert "Dimensions: 3" in result.output
            client.embed.assert_called_once_with("nomic-embed-text", "Hello world")

    def test_embed_text_json_format(self) -> None:
        """Should output embedding in JSON format."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.embed = AsyncMock(
                return_value={
                    "embedding": [0.1, 0.2, 0.3],
                    "total_duration": 1000000,
                }
            )
            MockClient.return_value = client

            result = runner.invoke(app, ["embed", "nomic-embed-text", "Test", "--format", "json"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["model"] == "nomic-embed-text"
            assert output["embedding"] == [0.1, 0.2, 0.3]
            assert output["dimensions"] == 3

    def test_embed_text_quiet_mode(self) -> None:
        """Should output only embedding array in quiet mode."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.embed = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
            MockClient.return_value = client

            result = runner.invoke(app, ["embed", "nomic-embed-text", "Test", "--quiet"])

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output == [0.1, 0.2, 0.3]

    def test_embed_file(self) -> None:
        """Should embed content from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Content from file")
            f.flush()

            try:
                with patch("miru.commands.embed.OllamaClient") as MockClient:
                    client = AsyncMock()
                    client.__aenter__ = AsyncMock(return_value=client)
                    client.__aexit__ = AsyncMock(return_value=None)
                    client.embed = AsyncMock(
                        return_value={
                            "embedding": [0.5, 0.6],
                            "total_duration": 2000000,
                        }
                    )
                    MockClient.return_value = client

                    result = runner.invoke(app, ["embed", "nomic-embed-text", "--file", f.name])

                    assert result.exit_code == 0
                    client.embed.assert_called_once()
                    call_args = client.embed.call_args[0]
                    assert "Content from file" in call_args[1]
            finally:
                Path(f.name).unlink()

    def test_embed_file_not_found(self) -> None:
        """Should error when file not found."""
        result = runner.invoke(app, ["embed", "nomic-embed-text", "--file", "nonexistent.txt"])

        assert result.exit_code == 1
        assert "não encontrado" in result.output

    def test_embed_batch_single_line(self) -> None:
        """Should embed single line from batch file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("First text\n")
            f.flush()

            try:
                with patch("miru.commands.embed.OllamaClient") as MockClient:
                    client = AsyncMock()
                    client.__aenter__ = AsyncMock(return_value=client)
                    client.__aexit__ = AsyncMock(return_value=None)
                    client.embed = AsyncMock(
                        return_value={"embedding": [0.1, 0.2], "total_duration": 1000000}
                    )
                    MockClient.return_value = client

                    result = runner.invoke(
                        app, ["embed", "nomic-embed-text", "--batch", f.name, "--format", "json"]
                    )

                    assert result.exit_code == 0
                    output = json.loads(result.output)
                    assert output["model"] == "nomic-embed-text"
                    assert len(output["results"]) == 1
                    assert output["results"][0]["line"] == 1
                    assert output["results"][0]["embedding"] == [0.1, 0.2]
            finally:
                Path(f.name).unlink()

    def test_embed_batch_multiple_lines(self) -> None:
        """Should embed multiple lines from batch file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("First line\nSecond line\nThird line\n")
            f.flush()

            try:
                with patch("miru.commands.embed.OllamaClient") as MockClient:
                    client = AsyncMock()
                    client.__aenter__ = AsyncMock(return_value=client)
                    client.__aexit__ = AsyncMock(return_value=None)
                    client.embed = AsyncMock(
                        side_effect=[
                            {"embedding": [0.1, 0.2], "total_duration": 1000000},
                            {"embedding": [0.3, 0.4], "total_duration": 1100000},
                            {"embedding": [0.5, 0.6], "total_duration": 1200000},
                        ]
                    )
                    MockClient.return_value = client

                    result = runner.invoke(
                        app, ["embed", "nomic-embed-text", "--batch", f.name, "--format", "json"]
                    )

                    assert result.exit_code == 0
                    output = json.loads(result.output)
                    assert len(output["results"]) == 3
                    assert client.embed.call_count == 3
            finally:
                Path(f.name).unlink()

    def test_embed_batch_jsonl_format(self) -> None:
        """Should output in JSONL format for batch."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Line 1\nLine 2\n")
            f.flush()

            try:
                with patch("miru.commands.embed.OllamaClient") as MockClient:
                    client = AsyncMock()
                    client.__aenter__ = AsyncMock(return_value=client)
                    client.__aexit__ = AsyncMock(return_value=None)
                    client.embed = AsyncMock(
                        return_value={"embedding": [0.1, 0.2], "total_duration": 1000000}
                    )
                    MockClient.return_value = client

                    result = runner.invoke(
                        app,
                        ["embed", "nomic-embed-text", "--batch", f.name, "--format", "jsonl"],
                    )

                    assert result.exit_code == 0
                    # Should be two JSON lines
                    lines = result.output.strip().split("\n")
                    assert len(lines) == 2
                    for line in lines:
                        obj = json.loads(line)
                        assert "line" in obj
                        assert "embedding" in obj
            finally:
                Path(f.name).unlink()

    def test_embed_batch_jsonl_with_json_input(self) -> None:
        """Should parse JSON lines in batch file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write('{"prompt": "First prompt"}\n')
            f.write('{"text": "Second text"}\n')
            f.write("Plain text line\n")
            f.flush()

            try:
                with patch("miru.commands.embed.OllamaClient") as MockClient:
                    client = AsyncMock()
                    client.__aenter__ = AsyncMock(return_value=client)
                    client.__aexit__ = AsyncMock(return_value=None)
                    client.embed = AsyncMock(
                        return_value={"embedding": [0.1, 0.2], "total_duration": 1000000}
                    )
                    MockClient.return_value = client

                    result = runner.invoke(
                        app,
                        ["embed", "nomic-embed-text", "--batch", f.name, "--format", "jsonl"],
                    )

                    assert result.exit_code == 0
                    # Verify embed was called with correct prompts
                    assert client.embed.call_count == 3
            finally:
                Path(f.name).unlink()

    def test_embed_model_not_found(self) -> None:
        """Should show error when model not found."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.embed = AsyncMock(side_effect=OllamaModelNotFound("not found"))
            MockClient.return_value = client

            result = runner.invoke(app, ["embed", "nonexistent-model", "test"])

            assert result.exit_code == 1
            assert "não encontrado" in result.output

    def test_embed_connection_error(self) -> None:
        """Should show error when Ollama offline."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            # Need to make async context manager raise error
            async def raise_connection_error():
                raise OllamaConnectionError("Cannot connect")

            client = AsyncMock()
            client.__aenter__ = AsyncMock(side_effect=OllamaConnectionError("Cannot connect"))
            client.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = client

            result = runner.invoke(app, ["embed", "nomic-embed-text", "test"])

            assert result.exit_code == 1

    def test_embed_no_input_provided(self) -> None:
        """Should error when no input provided."""
        result = runner.invoke(app, ["embed", "nomic-embed-text"])

        assert result.exit_code == 1
        assert "Forneça um texto" in result.output

    def test_embed_multiple_inputs(self) -> None:
        """Should error when multiple inputs provided."""
        result = runner.invoke(app, ["embed", "nomic-embed-text", "text", "--file", "file.txt"])

        assert result.exit_code == 1
        assert "apenas uma opção" in result.output

    def test_embed_invalid_format(self) -> None:
        """Should error with invalid format."""
        result = runner.invoke(app, ["embed", "nomic-embed-text", "test", "--format", "xml"])

        assert result.exit_code == 1
        assert "Invalid format" in result.output

    def test_embed_batch_jsonl_incompatible_with_file(self) -> None:
        """Should error when using --format jsonl with --file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            f.flush()

            try:
                result = runner.invoke(
                    app, ["embed", "nomic-embed-text", "--file", f.name, "--format", "jsonl"]
                )

                assert result.exit_code == 1
                assert "jsonl" in result.output.lower()
            finally:
                Path(f.name).unlink()

    def test_embed_custom_host(self) -> None:
        """Should use custom host when provided."""
        with patch("miru.commands.embed.OllamaClient") as MockClient:
            client = AsyncMock()
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            client.embed = AsyncMock(return_value={"embedding": [0.1]})
            MockClient.return_value = client

            result = runner.invoke(
                app, ["embed", "nomic-embed-text", "test", "--host", "http://custom:11434"]
            )

            assert result.exit_code == 0
            MockClient.assert_called_once_with("http://custom:11434")


class TestEmbedClient:
    """Tests for OllamaClient.embed method."""

    @pytest.mark.asyncio
    async def test_embed_basic(self) -> None:
        """Should call embed endpoint."""
        from unittest.mock import MagicMock
        import httpx

        from miru.ollama.client import OllamaClient

        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=MagicMock(json=lambda: {"embedding": [0.1, 0.2, 0.3]})
        )

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                result = await client.embed("nomic-embed-text", "Hello")

                assert result == {"embedding": [0.1, 0.2, 0.3]}
                mock_http_client.request.assert_called_once_with(
                    "POST",
                    "http://localhost:11434/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": "Hello"},
                )

    @pytest.mark.asyncio
    async def test_embed_with_options(self) -> None:
        """Should include options in request."""
        from unittest.mock import MagicMock
        import httpx

        from miru.ollama.client import OllamaClient

        client = OllamaClient(host="http://localhost:11434")

        mock_http_client = MagicMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=MagicMock(json=lambda: {"embedding": [0.1, 0.2]})
        )

        with patch.object(client, "_get_client", return_value=mock_http_client):
            async with client:
                result = await client.embed(
                    "nomic-embed-text",
                    "Hello",
                    options={"temperature": 0.5},
                )

                assert result == {"embedding": [0.1, 0.2]}
                call_args = mock_http_client.request.call_args
                body = call_args[1]["json"]
                assert "options" in body
                assert body["options"]["temperature"] == 0.5
