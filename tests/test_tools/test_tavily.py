"""Tests for Tavily tools."""

from unittest.mock import Mock, patch

import pytest

from miru.tools import (
    ToolRegistry,
    create_tavily_tools,
)
from miru.tools.tavily import (
    TavilyClient,
    TavilyError,
    _format_extract_results,
    _format_search_results,
)


class TestTavilyClient:
    """Tests for TavilyClient."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        client = TavilyClient(api_key="tvly-test-key")
        assert client.api_key == "tvly-test-key"

    @patch.dict("os.environ", {"MIRU_TAVILY_API_KEY": "tvly-env-key"}, clear=False)
    def test_init_with_env_key(self) -> None:
        """Test initialization from environment variable."""
        # Clear any config influence
        with patch("miru.tools.tavily.get_config_value", return_value=None):
            client = TavilyClient()
            assert client.api_key == "tvly-env-key"

    @patch("miru.tools.tavily.get_config_value")
    def test_init_with_config_key(self, mock_config: Mock) -> None:
        """Test initialization from config file."""
        mock_config.return_value = "tvly-config-key"
        client = TavilyClient()
        assert client.api_key == "tvly-config-key"

    def test_init_no_key_raises_error(self) -> None:
        """Test initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("miru.tools.tavily.get_config_value", return_value=None):
                with pytest.raises(TavilyError, match="API key not configured"):
                    TavilyClient()

    @patch("httpx.Client.post")
    def test_search_success(self, mock_post: Mock) -> None:
        """Test successful search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python Asyncio",
                    "url": "https://example.com/asyncio",
                    "content": "Asyncio docs",
                    "score": 0.95,
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_client_instance.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client_instance):
            client = TavilyClient(api_key="tvly-test")
            result = client.search("Python asyncio", max_results=5)

            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "Python Asyncio"

    @patch("httpx.Client.post")
    def test_search_with_images_success(self, mock_post: Mock) -> None:
        """Test successful search with images."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Python",
                    "url": "https://python.org",
                    "content": "Python language",
                    "score": 0.99,
                }
            ],
            "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_client_instance.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client_instance):
            client = TavilyClient(api_key="tvly-test")
            result = client.search_with_images("Python", max_results=5)

            assert "results" in result
            assert "images" in result
            assert len(result["images"]) == 2

    @patch("httpx.Client.post")
    def test_extract_success(self, mock_post: Mock) -> None:
        """Test successful extraction."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "content": "Extracted content",
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_client_instance = Mock()
        mock_client_instance.__enter__ = Mock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = Mock(return_value=None)
        mock_client_instance.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client_instance):
            client = TavilyClient(api_key="tvly-test")
            result = client.extract(["https://example.com"])

            assert "results" in result
            assert len(result["results"]) == 1


class TestCreateTavilyTools:
    """Tests for create_tavily_tools."""

    def test_creates_three_tools(self) -> None:
        """Test that three tools are created."""
        tools = create_tavily_tools(api_key="tvly-test")

        assert len(tools) == 3
        tool_names = {t.name for t in tools}
        assert tool_names == {"tavily_search", "tavily_search_images", "tavily_extract"}

    def test_tool_search_ollama_format(self) -> None:
        """Test search tool Ollama format."""
        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        ollama_format = search_tool.to_ollama_format()

        assert ollama_format["type"] == "function"
        assert ollama_format["function"]["name"] == "tavily_search"
        assert "query" in ollama_format["function"]["parameters"]["properties"]

    def test_tool_validate_arguments(self) -> None:
        """Test tool argument validation."""
        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        # Valid arguments
        errors = search_tool.validate_arguments({"query": "test"})
        assert errors == []

        # Missing required
        errors = search_tool.validate_arguments({})
        assert len(errors) == 1
        assert "query" in errors[0]

    def test_integration_with_registry(self) -> None:
        """Test registering tools in ToolRegistry."""
        registry = ToolRegistry()
        tools = create_tavily_tools(api_key="tvly-test")

        for tool in tools:
            registry.register(tool)

        assert len(registry) == 3
        assert "tavily_search" in registry
        assert "tavily_search_images" in registry
        assert "tavily_extract" in registry


class TestSearchTool:
    """Tests for tavily_search tool."""

    def test_search_empty_query(self) -> None:
        """Test search with empty query."""
        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        result = search_tool.handler(query="", max_results=5)
        assert "Error:" in result
        assert "empty" in result.lower()

    def test_search_invalid_max_results(self) -> None:
        """Test search with invalid max_results."""
        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        result = search_tool.handler(query="test", max_results=20)
        assert "Error:" in result

    @patch("miru.tools.tavily.TavilyClient.search")
    def test_search_success(self, mock_search: Mock) -> None:
        """Test successful search execution."""
        mock_search.return_value = {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "content": "Test content",
                    "score": 0.99,
                }
            ]
        }

        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        result = search_tool.handler(query="test query", max_results=5)

        assert "Test Result" in result
        assert "https://example.com" in result

    @patch("miru.tools.tavily.TavilyClient.search")
    def test_search_error(self, mock_search: Mock) -> None:
        """Test search error handling."""
        mock_search.side_effect = TavilyError("API error")

        tools = create_tavily_tools(api_key="tvly-test")
        search_tool = next(t for t in tools if t.name == "tavily_search")

        result = search_tool.handler(query="test", max_results=5)

        assert "Error:" in result


class TestSearchImagesTool:
    """Tests for tavily_search_images tool."""

    def test_search_images_empty_query(self) -> None:
        """Test search with images with empty query."""
        tools = create_tavily_tools(api_key="tvly-test")
        search_images_tool = next(t for t in tools if t.name == "tavily_search_images")

        result = search_images_tool.handler(query="", max_results=5)
        assert "Error:" in result

    @patch("miru.tools.tavily.TavilyClient.search_with_images")
    def test_search_images_success(self, mock_search: Mock) -> None:
        """Test successful search with images."""
        mock_search.return_value = {
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Content",
                    "score": 0.95,
                }
            ],
            "images": ["https://img1.jpg", "https://img2.jpg"],
        }

        tools = create_tavily_tools(api_key="tvly-test")
        search_images_tool = next(t for t in tools if t.name == "tavily_search_images")

        result = search_images_tool.handler(query="test", max_results=5)

        assert "Test" in result
        assert "Related Images" in result


class TestExtractTool:
    """Tests for tavily_extract tool."""

    def test_extract_empty_urls(self) -> None:
        """Test extract with empty URLs."""
        tools = create_tavily_tools(api_key="tvly-test")
        extract_tool = next(t for t in tools if t.name == "tavily_extract")

        result = extract_tool.handler(urls="")
        assert "Error:" in result

    @patch("miru.tools.tavily.TavilyClient.extract")
    def test_extract_success(self, mock_extract: Mock) -> None:
        """Test successful extraction."""
        mock_extract.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "content": "Extracted content",
                }
            ]
        }

        tools = create_tavily_tools(api_key="tvly-test")
        extract_tool = next(t for t in tools if t.name == "tavily_extract")

        result = extract_tool.handler(urls="https://example.com")

        assert "Extracted Content" in result
        assert "https://example.com" in result

    def test_extract_multiple_urls(self) -> None:
        """Test extract with multiple URLs."""
        tools = create_tavily_tools(api_key="tvly-test")
        extract_tool = next(t for t in tools if t.name == "tavily_extract")

        # Validate parameter parsing
        errors = extract_tool.validate_arguments({"urls": "url1.com, url2.com"})
        assert errors == []


class TestFormatting:
    """Tests for result formatting."""

    def test_format_search_results(self) -> None:
        """Test search result formatting."""
        result = {
            "results": [
                {
                    "title": "Python",
                    "url": "https://python.org",
                    "content": "Python programming",
                    "score": 0.99,
                }
            ]
        }

        formatted = _format_search_results(result, "Python")

        assert "# Search Results" in formatted
        assert "Python" in formatted
        assert "https://python.org" in formatted
        assert "Score: 0.99" in formatted

    def test_format_search_results_with_images(self) -> None:
        """Test search result formatting with images."""
        result = {
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "content": "Content",
                    "score": 0.95,
                }
            ],
            "images": ["https://img1.jpg", "https://img2.jpg"],
        }

        formatted = _format_search_results(result, "test", include_images=True)

        assert "Related Images" in formatted
        assert "https://img1.jpg" in formatted

    def test_format_extract_results(self) -> None:
        """Test extract result formatting."""
        result = {
            "results": [
                {
                    "url": "https://example.com",
                    "content": "Extracted text",
                }
            ]
        }

        formatted = _format_extract_results(result)

        assert "# Extracted Content" in formatted
        assert "https://example.com" in formatted
        assert "Extracted text" in formatted