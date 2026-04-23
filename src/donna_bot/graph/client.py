"""Async Microsoft Graph API client using httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from donna_bot.auth.token_manager import TokenManager

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MAX_RETRIES = 3
TIMEOUT = 30.0


class GraphClient:
    """Async HTTP client for Microsoft Graph API with retry on 429."""

    def __init__(self, token_manager: TokenManager) -> None:
        self._tm = token_manager
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=GRAPH_BASE,
                timeout=TIMEOUT,
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        self._tm.ensure_token()
        return self._tm.auth_headers

    async def get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """GET request to Graph API with retry on 429."""
        client = await self._ensure_client()

        for attempt in range(MAX_RETRIES):
            resp = await client.get(path, headers=self._headers(), params=params)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("Throttled (429) — retry %d in %ds", attempt + 1, retry_after)
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json()

        resp.raise_for_status()
        return {}

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request to Graph API with retry on 429."""
        client = await self._ensure_client()

        for attempt in range(MAX_RETRIES):
            resp = await client.post(path, headers=self._headers(), json=json)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("Throttled (429) — retry %d in %ds", attempt + 1, retry_after)
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json()

        resp.raise_for_status()
        return {}

    async def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """PATCH request to Graph API with retry on 429."""
        client = await self._ensure_client()

        for attempt in range(MAX_RETRIES):
            resp = await client.patch(path, headers=self._headers(), json=json)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("Throttled (429) — retry %d in %ds", attempt + 1, retry_after)
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code == 204:
                return {}
            resp.raise_for_status()
            return resp.json()

        resp.raise_for_status()
        return {}

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
