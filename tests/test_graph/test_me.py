"""Tests for Graph /me module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from donna_bot.graph.me import get_presence, get_profile


@pytest.fixture
def mock_graph() -> MagicMock:
    g = MagicMock()
    g.get = AsyncMock()
    g.post = AsyncMock()
    return g


class TestGetProfile:
    async def test_returns_display_name(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "displayName": "Harshit Gupta",
            "mail": "harshitg@microsoft.com",
            "jobTitle": "Senior SDE",
            "officeLocation": "Bangalore",
            "department": "Platform",
            "userPrincipalName": "harshitg@microsoft.com",
        }
        result = await get_profile(mock_graph)
        assert result["displayName"] == "Harshit Gupta"
        assert result["mail"] == "harshitg@microsoft.com"
        assert result["jobTitle"] == "Senior SDE"

    async def test_handles_missing_fields(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {"displayName": "Harvey"}
        result = await get_profile(mock_graph)
        assert result["displayName"] == "Harvey"
        assert result["mail"] == ""
        assert result["jobTitle"] == ""


class TestGetPresence:
    async def test_returns_availability(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "availability": "Available",
            "activity": "Available",
        }
        result = await get_presence(mock_graph)
        assert result["availability"] == "Available"

    async def test_defaults_to_offline(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {}
        result = await get_presence(mock_graph)
        assert result["availability"] == "Offline"
