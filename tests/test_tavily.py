"""Tests for miru/tools/tavily.py — client errors and tool wrappers."""

import httpx
import pytest

from miru.tools.tavily import TavilyClient, TavilyError, create_tavily_tools


class TestTavilyClientErrors:
    def test_missing_api_key(self) -> None:
        with pytest.raises(TavilyError):
            TavilyClient(None)

    def test_search_http_error(self, monkeypatch) -> None:
        client = TavilyClient("tvly-test")

        class FakeResponse:
            status_code = 401
            text = "unauthorized"

            def raise_for_status(self):
                raise httpx.HTTPStatusError("401", request=httpx.Request("POST", "http://x"), response=self)

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **k):
                return FakeResponse()

        monkeypatch.setattr("httpx.Client", lambda *a, **k: FakeClient())
        with pytest.raises(TavilyError):
            client.search("query")

    def test_search_request_error(self, monkeypatch) -> None:
        client = TavilyClient("tvly-test")

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, *a, **k):
                raise httpx.RequestError("no network")

        monkeypatch.setattr("httpx.Client", lambda *a, **k: FakeClient())
        with pytest.raises(TavilyError):
            client.search("query")


class TestTavilyTools:
    def test_create_requires_key(self) -> None:
        with pytest.raises(TavilyError):
            create_tavily_tools(None)

    def test_tools_created_with_key(self, monkeypatch) -> None:
        monkeypatch.setattr("miru.tools.tavily.TavilyClient", lambda k: object())
        tools = create_tavily_tools("tvly-x")
        assert len(tools) >= 1
