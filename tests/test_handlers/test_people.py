"""Tests for people handler + graph/people module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes, ConversationHandler

from donna_bot.graph.people import (
    _parse_person,
    _parse_user,
    get_direct_reports,
    get_manager,
    get_org_chain,
    get_user_presence,
    search_people,
)
from donna_bot.handlers.people import (
    _format_org_chart,
    _format_search_results,
    build_people_conversation,
    detail_callback,
    org_callback,
    search_callback,
    who_command,
)
from donna_bot.state.machine import State


# ── Fixtures ────────────────────────────────────────────────────────────

SAMPLE_PEOPLE = [
    {
        "id": "u-001",
        "name": "Satya Nadella",
        "email": "satya@microsoft.com",
        "title": "CEO",
        "department": "Executive",
        "location": "Redmond",
        "upn": "satya@microsoft.com",
    },
    {
        "id": "u-002",
        "name": "Amy Hood",
        "email": "amy@microsoft.com",
        "title": "CFO",
        "department": "Finance",
        "location": "Redmond",
        "upn": "amy@microsoft.com",
    },
]


def _make_update(chat_id: int = 496116833, text: str = "/who Satya") -> Update:
    user = User(id=chat_id, first_name="Harshit", is_bot=False)
    chat = Chat(id=chat_id, type="private")
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.from_user = user
    msg.chat = chat
    msg.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_chat = chat
    update.effective_user = user
    update.message = msg
    update.callback_query = None
    return update


def _make_callback_update(data: str, chat_id: int = 496116833) -> Update:
    user = User(id=chat_id, first_name="Harshit", is_bot=False)
    chat = Chat(id=chat_id, type="private")

    query = MagicMock(spec=CallbackQuery)
    query.data = data
    query.from_user = user
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_chat = chat
    update.effective_user = user
    update.callback_query = query
    update.message = None
    return update


def _make_context(graph: AsyncMock | None = None, args: list[str] | None = None) -> ContextTypes.DEFAULT_TYPE:
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    settings = MagicMock()
    settings.harvey_chat_id = 496116833

    ctx.bot_data = {
        "settings": settings,
        "graph": graph,
    }
    ctx.user_data = {}
    ctx.args = args or []
    return ctx


# ── Graph People Module Tests ───────────────────────────────────────────

class TestParsePerson:
    def test_parses_fields(self):
        raw = {
            "id": "abc",
            "displayName": "John Doe",
            "emailAddresses": [{"address": "john@example.com"}],
            "jobTitle": "Engineer",
            "department": "Engineering",
            "officeLocation": "Building 42",
            "userPrincipalName": "john@example.com",
        }
        result = _parse_person(raw)
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert result["title"] == "Engineer"

    def test_handles_no_email(self):
        raw = {"id": "x", "displayName": "Nobody", "emailAddresses": []}
        result = _parse_person(raw)
        assert result["email"] == ""

    def test_handles_missing_fields(self):
        raw = {}
        result = _parse_person(raw)
        assert result["name"] == "?"
        assert result["email"] == ""


class TestParseUser:
    def test_parses_user(self):
        raw = {
            "id": "u1",
            "displayName": "Jane",
            "mail": "jane@example.com",
            "jobTitle": "PM",
            "department": "Product",
            "officeLocation": "HQ",
            "mobilePhone": "+1234",
            "companyName": "Contoso",
        }
        result = _parse_user(raw)
        assert result["name"] == "Jane"
        assert result["phone"] == "+1234"
        assert result["company"] == "Contoso"


class TestSearchPeople:
    @pytest.mark.asyncio
    async def test_search_returns_parsed(self):
        graph = AsyncMock()
        graph.get.return_value = {
            "value": [
                {
                    "id": "p1",
                    "displayName": "Alice",
                    "emailAddresses": [{"address": "alice@contoso.com"}],
                    "jobTitle": "Dev",
                    "department": "Eng",
                    "officeLocation": "Remote",
                },
            ],
        }
        result = await search_people(graph, "Alice")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        graph.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_results(self):
        graph = AsyncMock()
        graph.get.return_value = {"value": []}
        result = await search_people(graph, "Nobody")
        assert result == []


class TestGetUserPresence:
    @pytest.mark.asyncio
    async def test_returns_presence(self):
        graph = AsyncMock()
        graph.get.return_value = {"availability": "Available", "activity": "Available"}
        result = await get_user_presence(graph, "u1")
        assert result["availability"] == "Available"

    @pytest.mark.asyncio
    async def test_error_returns_unknown(self):
        graph = AsyncMock()
        graph.get.side_effect = Exception("Network")
        result = await get_user_presence(graph, "u1")
        assert result["availability"] == "PresenceUnknown"


class TestGetManager:
    @pytest.mark.asyncio
    async def test_returns_manager(self):
        graph = AsyncMock()
        graph.get.return_value = {
            "id": "mgr1", "displayName": "Boss", "mail": "boss@example.com",
            "jobTitle": "Director", "department": "Eng",
        }
        result = await get_manager(graph, "u1")
        assert result is not None
        assert result["name"] == "Boss"

    @pytest.mark.asyncio
    async def test_no_manager(self):
        graph = AsyncMock()
        graph.get.side_effect = Exception("404")
        result = await get_manager(graph, "u1")
        assert result is None


class TestGetDirectReports:
    @pytest.mark.asyncio
    async def test_returns_reports(self):
        graph = AsyncMock()
        graph.get.return_value = {
            "value": [
                {"id": "r1", "displayName": "Report1", "mail": "r1@example.com", "jobTitle": "SDE"},
            ],
        }
        result = await get_direct_reports(graph, "u1")
        assert len(result) == 1
        assert result[0]["name"] == "Report1"

    @pytest.mark.asyncio
    async def test_error_returns_empty(self):
        graph = AsyncMock()
        graph.get.side_effect = Exception("Error")
        result = await get_direct_reports(graph, "u1")
        assert result == []


class TestGetOrgChain:
    @pytest.mark.asyncio
    async def test_walks_chain(self):
        graph = AsyncMock()
        # First call returns manager, second returns their manager, third fails
        graph.get.side_effect = [
            {"id": "mgr1", "displayName": "Manager", "mail": "m@x.com", "jobTitle": "Dir"},
            {"id": "mgr2", "displayName": "VP", "mail": "vp@x.com", "jobTitle": "VP"},
            Exception("No more"),
        ]
        result = await get_org_chain(graph, "u1", depth=3)
        assert len(result) == 2
        assert result[0]["name"] == "Manager"
        assert result[1]["name"] == "VP"


# ── People Handler Tests ────────────────────────────────────────────────

class TestSearchResultsFormatter:
    def test_renders_results(self):
        text = _format_search_results(SAMPLE_PEOPLE, "Satya")
        assert "PEOPLE" in text
        assert "Satya Nadella" in text
        assert "CEO" in text

    def test_renders_empty(self):
        text = _format_search_results([], "Nobody")
        assert "Nobody found" in text


class TestOrgChartFormatter:
    def test_renders_full_chart(self):
        person = {"name": "Harvey", "title": "PM"}
        chain = [{"name": "Boss", "title": "Director"}]
        reports = [{"name": "Junior", "title": "SDE"}]
        text = _format_org_chart(person, chain, reports)
        assert "ORG CHART" in text
        assert "Harvey" in text
        assert "Boss" in text
        assert "Junior" in text

    def test_no_reports(self):
        person = {"name": "Harvey", "title": "PM"}
        text = _format_org_chart(person, [], [])
        assert "No direct reports" in text


class TestWhoCommand:
    @pytest.mark.asyncio
    async def test_no_graph(self):
        update = _make_update()
        ctx = _make_context(graph=None)
        result = await who_command(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_no_query(self):
        update = _make_update(text="/who")
        ctx = _make_context(graph=AsyncMock(), args=[])
        result = await who_command(update, ctx)
        assert result == ConversationHandler.END
        # Should show usage hint
        call_args = update.message.reply_text.call_args
        assert "Usage" in str(call_args) or "who" in str(call_args)

    @pytest.mark.asyncio
    async def test_successful_search(self):
        update = _make_update()
        ctx = _make_context(graph=AsyncMock(), args=["Satya"])

        with patch(
            "donna_bot.handlers.people.search_people",
            return_value=SAMPLE_PEOPLE,
        ):
            result = await who_command(update, ctx)

        assert result == State.PEOPLE_SEARCH
        assert ctx.user_data["people_results"] == SAMPLE_PEOPLE

    @pytest.mark.asyncio
    async def test_search_error(self):
        update = _make_update()
        ctx = _make_context(graph=AsyncMock(), args=["Satya"])

        with patch(
            "donna_bot.handlers.people.search_people",
            side_effect=Exception("API error"),
        ):
            result = await who_command(update, ctx)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = _make_update(chat_id=999)
        ctx = _make_context(graph=AsyncMock(), args=["Satya"])
        result = await who_command(update, ctx)
        assert result is None


class TestSearchCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_callback_update("who:close")
        ctx = _make_context(graph=AsyncMock())
        result = await search_callback(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_select_person(self):
        update = _make_callback_update("who:select:0")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["people_results"] = SAMPLE_PEOPLE

        with patch(
            "donna_bot.handlers.people.get_user_presence",
            return_value={"availability": "Available", "activity": "Available"},
        ):
            result = await search_callback(update, ctx)

        assert result == State.PEOPLE_DETAIL

    @pytest.mark.asyncio
    async def test_select_out_of_range(self):
        update = _make_callback_update("who:select:99")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["people_results"] = SAMPLE_PEOPLE

        result = await search_callback(update, ctx)
        assert result == State.PEOPLE_SEARCH


class TestDetailCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_callback_update("who:close")
        ctx = _make_context(graph=AsyncMock())
        result = await detail_callback(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_back(self):
        update = _make_callback_update("who:back")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["people_results"] = SAMPLE_PEOPLE
        ctx.user_data["people_query"] = "Satya"

        result = await detail_callback(update, ctx)
        assert result == State.PEOPLE_SEARCH

    @pytest.mark.asyncio
    async def test_org_chart(self):
        update = _make_callback_update("who:org:u-001")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["current_person"] = SAMPLE_PEOPLE[0]

        with patch(
            "donna_bot.handlers.people.get_org_chain",
            return_value=[{"name": "CEO's Boss", "title": "Board"}],
        ), patch(
            "donna_bot.handlers.people.get_direct_reports",
            return_value=[{"name": "Report", "title": "IC"}],
        ):
            result = await detail_callback(update, ctx)

        assert result == State.ORG_CHART


class TestOrgCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_callback_update("who:close")
        ctx = _make_context(graph=AsyncMock())
        result = await org_callback(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_back_to_detail(self):
        update = _make_callback_update("who:detail:u-001")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["current_person"] = SAMPLE_PEOPLE[0]

        with patch(
            "donna_bot.handlers.people.get_user_presence",
            return_value={"availability": "Busy"},
        ):
            result = await org_callback(update, ctx)

        assert result == State.PEOPLE_DETAIL


class TestBuildConversation:
    def test_builds_handler(self):
        handler = build_people_conversation()
        assert handler is not None
        assert handler.name == "people_flow"
