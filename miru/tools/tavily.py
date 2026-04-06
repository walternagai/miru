"""Tavily API client and web search tools."""

from __future__ import annotations

import os
from typing import Any

import httpx

from miru.config_manager import get_config_value
from miru.tools.base import Tool, create_tool, get_tool_from_function


class TavilyError(Exception):
    """Error from Tavily API."""
    pass


class TavilyClient:
    """Client for Tavily API."""
    
    API_URL = "https://api.tavily.com"
    
    def __init__(self, api_key: str | None = None):
        """Initialize Tavily client.
        
        Args:
            api_key: Tavily API key. If None, reads from config/env.
        
        Raises:
            TavilyError: If API key not available
        """
        self.api_key = api_key or self._get_api_key()
        
        if not self.api_key:
            raise TavilyError(
                "Tavily API key not configured. "
                "Set via: miru config set tavily_api_key YOUR_KEY "
                "or environment variable MIRU_TAVILY_API_KEY"
            )
    
    def _get_api_key(self) -> str | None:
        """Get API key from config or environment."""
        # First check environment variable
        env_key = os.environ.get("MIRU_TAVILY_API_KEY")
        if env_key:
            return env_key
        
        # Then check config file
        config_key = get_config_value("tavily_api_key")
        if config_key:
            return str(config_key)
        
        return None
    
    def search(
        self, 
        query: str, 
        max_results: int = 10
    ) -> dict[str, Any]:
        """Search the web.
        
        Args:
            query: Search query
            max_results: Maximum results (1-10)
        
        Returns:
            Search results dict
        
        Raises:
            TavilyError: If API call fails
        """
        url = f"{self.API_URL}/search"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": query,
                        "max_results": max_results,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise TavilyError(f"API error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise TavilyError(f"Request failed: {e}") from e
    
    def search_with_images(
        self, 
        query: str, 
        max_results: int = 10
    ) -> dict[str, Any]:
        """Search web with image results.
        
        Args:
            query: Search query
            max_results: Maximum results (1-10)
        
        Returns:
            Search results with images
        """
        url = f"{self.API_URL}/search"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": query,
                        "max_results": max_results,
                        "include_images": True,
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise TavilyError(f"API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TavilyError(f"Request failed: {e}") from e
    
    def extract(self, urls: list[str]) -> dict[str, Any]:
        """Extract content from URLs.
        
        Args:
            urls: List of URLs to extract
        
        Returns:
            Extracted content
        """
        url = f"{self.API_URL}/extract"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"urls": urls}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise TavilyError(f"API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise TavilyError(f"Request failed: {e}") from e


def create_tavily_tools(api_key: str | None = None) -> list[Tool]:
    """Create Tavily web search tools.
    
    Args:
        api_key: Optional API key. Uses config/env if not provided.
    
    Returns:
        List of Tool instances
    
    Raises:
        TavilyError: If API key not configured
    """
    client = TavilyClient(api_key)
    
    def tavily_search(query: str, max_results: int = 10) -> str:
        """Search the web using Tavily.
        
        Args:
            query: Search query
            max_results: Maximum results to return (default: 10)
        
        Returns:
            Formatted search results as markdown
        """
        if not query or not query.strip():
            return "Error: Query cannot be empty"
        
        if not (1 <= max_results <= 10):
            return "Error: max_results must be between 1 and 10"
        
        try:
            result = client.search(query, max_results)
            return _format_search_results(result, query)
        except TavilyError as e:
            return f"Error: {e}"
    
    def tavily_search_images(query: str, max_results: int = 10) -> str:
        """Search the web and include related images.
        
        Args:
            query: Search query
            max_results: Maximum results (default: 10)
        
        Returns:
            Formatted results with images
        """
        if not query or not query.strip():
            return "Error: Query cannot be empty"
        
        if not (1 <= max_results <= 10):
            return "Error: max_results must be between 1 and 10"
        
        try:
            result = client.search_with_images(query, max_results)
            return _format_search_results(result, query, include_images=True)
        except TavilyError as e:
            return f"Error: {e}"
    
    def tavily_extract(urls: str) -> str:
        """Extract and clean content from URLs.
        
        Args:
            urls: Comma-separated list of URLs
        
        Returns:
            Extracted and cleaned content
        """
        if not urls or not urls.strip():
            return "Error: URLs cannot be empty"
        
        # Parse URLs (can be comma-separated)
        url_list = [u.strip() for u in urls.split(",") if u.strip()]
        
        if not url_list:
            return "Error: No valid URLs provided"
        
        try:
            result = client.extract(url_list)
            return _format_extract_results(result)
        except TavilyError as e:
            return f"Error: {e}"
    
    # Create Tool objects
    tools = [
        create_tool(
            name="tavily_search",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 10)"
                    }
                },
                "required": ["query"]
            }
        )(tavily_search),
        create_tool(
            name="tavily_search_images",
            description="Search the web and include related images in results",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        )(tavily_search_images),
        create_tool(
            name="tavily_extract",
            description="Extract and clean content from web pages",
            parameters={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "string",
                        "description": "Comma-separated list of URLs to extract"
                    }
                },
                "required": ["urls"]
            }
        )(tavily_extract),
    ]
    
    # Extract Tool objects
    extracted: list[Tool] = []
    for func in tools:
        tool = get_tool_from_function(func)
        if tool is not None:
            extracted.append(tool)
    
    return extracted


def _format_search_results(
    result: dict[str, Any], 
    query: str,
    include_images: bool = False
) -> str:
    """Format search results as markdown."""
    lines = [f"# Search Results for \"{query}\"\n"]
    
    # Format main results
    if "results" in result:
        for i, item in enumerate(result["results"], 1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = item.get("content", "")
            score = item.get("score", 0)
            
            lines.append(f"## Result {i} (Score: {score:.2f})")
            lines.append(f"**Title**: {title}")
            lines.append(f"**URL**: {url}")
            lines.append(f"**Content**: {content}\n")
    
    # Format images if present
    if include_images and "images" in result:
        lines.append("## Related Images\n")
        for img_url in result["images"][:5]:  # Limit to 5 images
            lines.append(f"- {img_url}")
    
    return "\n".join(lines)


def _format_extract_results(result: dict[str, Any]) -> str:
    """Format extract results as markdown."""
    lines = ["# Extracted Content\n"]
    
    if "results" in result:
        for item in result["results"]:
            url = item.get("url", "Unknown URL")
            content = item.get("content", "No content extracted")
            
            lines.append(f"## From: {url}\n")
            lines.append(f"**Content**: {content}\n")
    
    return "\n".join(lines)


__all__ = [
    "TavilyClient",
    "TavilyError",
    "create_tavily_tools",
]