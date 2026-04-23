"""Tests for async Graph client."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from donna_bot.graph.client import GraphClient

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@pytest.fixture
def graph_client(mock_token: str) -> GraphClient:
    tm = MagicMock()
    tm.ensure_token.return_value = mock_token
    tm.auth_headers = {
        "Authorization": f"Bearer {mock_token}",
        "Content-Type": "application/json",
    }
    return GraphClient(token_manager=tm)


class TestGraphClient:
    @respx.mock
    async def test_get_me(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me").mock(
            return_value=httpx.Response(200, json={
                "displayName": "Harvey Gupta",
                "mail": "harvey@microsoft.com",
            })
        )
        data = await graph_client.get("/me")
        assert data["displayName"] == "Harvey Gupta"

    @respx.mock
    async def test_get_with_params(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me/messages").mock(
            return_value=httpx.Response(200, json={"value": [{"subject": "Test"}]})
        )
        data = await graph_client.get("/me/messages", params={"$top": "5"})
        assert len(data["value"]) == 1

    @respx.mock
    async def test_post_search(self, graph_client: GraphClient) -> None:
        respx.post(f"{GRAPH_BASE}/search/query").mock(
            return_value=httpx.Response(200, json={"value": []})
        )
        data = await graph_client.post("/search/query", json={"requests": []})
        assert data["value"] == []

    @respx.mock
    async def test_handles_401(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me").mock(
            return_value=httpx.Response(401, json={"error": {"message": "Unauthorized"}})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await graph_client.get("/me")

    @respx.mock
    async def test_handles_429_retry(self, graph_client: GraphClient) -> None:
        route = respx.get(f"{GRAPH_BASE}/me")
        route.side_effect = [
            httpx.Response(429, headers={"Retry-After": "0"}, json={"error": {"message": "Throttled"}}),
            httpx.Response(200, json={"displayName": "Harvey"}),
        ]
        data = await graph_client.get("/me")
        assert data["displayName"] == "Harvey"
        assert route.call_count == 2
