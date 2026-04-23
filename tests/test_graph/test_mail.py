"""Tests for Graph Mail module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from donna_bot.graph.mail import get_email, get_inbox, get_unread, reply


@pytest.fixture
def mock_graph() -> MagicMock:
    g = MagicMock()
    g.get = AsyncMock()
    g.post = AsyncMock()
    return g


def _make_email(subject: str, sender: str = "Priya", is_read: bool = False) -> dict:
    return {
        "id": f"AAMk{hash(subject) % 10000}",
        "subject": subject,
        "from": {"emailAddress": {"name": sender, "address": f"{sender.lower()}@ms.com"}},
        "receivedDateTime": "2026-04-23T09:15:00Z",
        "bodyPreview": f"Preview of {subject}",
        "isRead": is_read,
        "hasAttachments": False,
        "importance": "normal",
    }


class TestGetUnread:
    async def test_returns_unread_emails(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "value": [
                _make_email("Design spec sign-off", "Priya"),
                _make_email("Migration timeline", "Manager"),
            ]
        }
        result = await get_unread(mock_graph, top=5)
        assert len(result) == 2
        assert result[0]["subject"] == "Design spec sign-off"
        assert result[0]["from"] == "Priya"
        assert result[0]["isRead"] is False

    async def test_empty_inbox(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {"value": []}
        result = await get_unread(mock_graph)
        assert result == []


class TestGetInbox:
    async def test_returns_with_count(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "value": [_make_email("Test", is_read=True)],
            "@odata.count": 42,
        }
        result = await get_inbox(mock_graph, top=10)
        assert result["total"] == 42
        assert len(result["emails"]) == 1


class TestGetEmail:
    async def test_returns_full_email(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "id": "AAMk123",
            "subject": "Design spec",
            "from": {"emailAddress": {"name": "Priya", "address": "priya@ms.com"}},
            "toRecipients": [
                {"emailAddress": {"name": "Harvey", "address": "harvey@ms.com"}},
            ],
            "receivedDateTime": "2026-04-23T09:15:00Z",
            "body": {"contentType": "Text", "content": "The spec is ready for review."},
            "hasAttachments": False,
            "importance": "normal",
            "conversationId": "conv123",
        }
        result = await get_email(mock_graph, "AAMk123")
        assert result["subject"] == "Design spec"
        assert "spec is ready" in result["body"]
        assert result["to"] == ["Harvey"]


class TestReply:
    async def test_calls_graph_post(self, mock_graph: MagicMock) -> None:
        mock_graph.post.return_value = {}
        await reply(mock_graph, "AAMk123", "LGTM, approved.")
        mock_graph.post.assert_called_once()
        call_args = mock_graph.post.call_args
        assert "AAMk123/reply" in call_args[0][0]
