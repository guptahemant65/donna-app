"""Tests for graph/search.py — M365 cross-tenant search."""

from __future__ import annotations

import pytest

from donna_bot.graph.search import (
    _extract_sender,
    _parse_hit,
    _type_key,
    search_m365,
)


# ── Unit Tests: Type Key Mapping ────────────────────────────────────────


class TestTypeKey:
    def test_message(self):
        assert _type_key("#microsoft.graph.message") == "emails"

    def test_drive_item(self):
        assert _type_key("#microsoft.graph.driveItem") == "files"

    def test_event(self):
        assert _type_key("#microsoft.graph.event") == "events"

    def test_list_item(self):
        assert _type_key("#microsoft.graph.listItem") == "lists"

    def test_chat_message(self):
        assert _type_key("#microsoft.graph.chatMessage") == "chats"

    def test_unknown(self):
        assert _type_key("#microsoft.graph.whatever") == "other"


# ── Unit Tests: Parse Hit ───────────────────────────────────────────────


class TestParseHit:
    def test_email_hit(self):
        hit = {
            "rank": 1,
            "summary": "test <c0>summary</c0>",
            "resource": {
                "@odata.type": "#microsoft.graph.message",
                "id": "msg-123",
                "subject": "Design Review",
                "sender": {
                    "emailAddress": {"name": "Alice", "address": "alice@ms.com"},
                },
                "receivedDateTime": "2025-01-15T10:00:00Z",
                "bodyPreview": "Please review the design doc for the new feature.",
                "webLink": "https://outlook.office.com/mail/msg-123",
            },
        }
        result = _parse_hit(hit, "#microsoft.graph.message")
        assert result["type"] == "email"
        assert result["subject"] == "Design Review"
        assert result["from"] == "Alice"
        assert result["webLink"] == "https://outlook.office.com/mail/msg-123"
        assert result["id"] == "msg-123"
        assert result["rank"] == 1

    def test_file_hit(self):
        hit = {
            "rank": 2,
            "summary": "",
            "resource": {
                "@odata.type": "#microsoft.graph.driveItem",
                "id": "file-456",
                "name": "Architecture.docx",
                "webUrl": "https://sharepoint.com/file",
                "lastModifiedDateTime": "2025-01-10T09:00:00Z",
                "size": 102400,
                "createdBy": {"user": {"displayName": "Bob"}},
            },
        }
        result = _parse_hit(hit, "#microsoft.graph.driveItem")
        assert result["type"] == "file"
        assert result["name"] == "Architecture.docx"
        assert result["createdBy"] == "Bob"
        assert result["size"] == 102400

    def test_event_hit(self):
        hit = {
            "rank": 3,
            "summary": "",
            "resource": {
                "@odata.type": "#microsoft.graph.event",
                "id": "evt-789",
                "subject": "Sprint Planning",
                "start": {"dateTime": "2025-01-20T14:00:00"},
                "end": {"dateTime": "2025-01-20T15:00:00"},
                "organizer": {"emailAddress": {"name": "Carol"}},
            },
        }
        result = _parse_hit(hit, "#microsoft.graph.event")
        assert result["type"] == "event"
        assert result["subject"] == "Sprint Planning"
        assert result["organizer"] == "Carol"

    def test_unknown_type(self):
        hit = {
            "rank": 4,
            "summary": "",
            "resource": {
                "@odata.type": "#microsoft.graph.unknown",
                "id": "x",
                "name": "Something",
            },
        }
        result = _parse_hit(hit, "#microsoft.graph.unknown")
        assert result["type"] == "other"
        assert result["name"] == "Something"

    def test_missing_fields(self):
        hit = {"resource": {"@odata.type": "#microsoft.graph.message"}}
        result = _parse_hit(hit, "#microsoft.graph.message")
        assert result["type"] == "email"
        assert result["subject"] == "(No subject)"
        assert result["from"] == "?"


# ── Unit Tests: Extract Sender ──────────────────────────────────────────


class TestExtractSender:
    def test_sender_with_name(self):
        resource = {"sender": {"emailAddress": {"name": "Alice", "address": "a@ms.com"}}}
        assert _extract_sender(resource) == "Alice"

    def test_from_field(self):
        resource = {"from": {"emailAddress": {"name": "Bob"}}}
        assert _extract_sender(resource) == "Bob"

    def test_address_fallback(self):
        resource = {"sender": {"emailAddress": {"address": "c@ms.com"}}}
        assert _extract_sender(resource) == "c@ms.com"

    def test_empty(self):
        assert _extract_sender({}) == "?"


# ── Integration Tests: search_m365 ──────────────────────────────────────


class TestSearchM365:
    @pytest.mark.asyncio
    async def test_search_returns_grouped_results(self):
        """Mock GraphClient to test full search pipeline."""
        search_response = {
            "value": [
                {
                    "hitsContainers": [
                        {
                            "hits": [
                                {
                                    "rank": 1,
                                    "summary": "test",
                                    "resource": {
                                        "@odata.type": "#microsoft.graph.message",
                                        "id": "m1",
                                        "subject": "Test Email",
                                        "sender": {"emailAddress": {"name": "Donna"}},
                                        "receivedDateTime": "2025-01-15",
                                        "bodyPreview": "Hello",
                                    },
                                },
                            ],
                        },
                    ],
                },
                {
                    "hitsContainers": [
                        {
                            "hits": [
                                {
                                    "rank": 1,
                                    "summary": "",
                                    "resource": {
                                        "@odata.type": "#microsoft.graph.driveItem",
                                        "id": "f1",
                                        "name": "test.docx",
                                        "webUrl": "https://sp.com/test",
                                    },
                                },
                            ],
                        },
                    ],
                },
            ],
        }

        class MockGraph:
            async def post(self, path, **kwargs):
                assert path == "/search/query"
                return search_response

        results = await search_m365(MockGraph(), "test query")
        assert "emails" in results
        assert "files" in results
        assert len(results["emails"]) == 1
        assert results["emails"][0]["subject"] == "Test Email"
        assert results["files"][0]["name"] == "test.docx"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        class MockGraph:
            async def post(self, path, **kwargs):
                return {"value": [{"hitsContainers": [{"hits": None}]}]}

        results = await search_m365(MockGraph(), "nothing")
        assert results == {}

    @pytest.mark.asyncio
    async def test_no_value(self):
        class MockGraph:
            async def post(self, path, **kwargs):
                return {"value": []}

        results = await search_m365(MockGraph(), "empty")
        assert results == {}

    @pytest.mark.asyncio
    async def test_custom_entity_types(self):
        class MockGraph:
            async def post(self, path, **kwargs):
                payload = kwargs.get("json", {})
                entity_types = [r["entityTypes"][0] for r in payload["requests"]]
                assert entity_types == ["event"]
                return {"value": []}

        await search_m365(MockGraph(), "query", entity_types=["event"])
