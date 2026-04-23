"""Tests for calendar ConversationHandler — every state transition."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes, ConversationHandler

from donna_bot.handlers.calendar import (
    _format_day_text,
    _format_week_text,
    _day_keyboard,
    _generate_talking_points,
    build_calendar_conversation,
    cal_command,
    cal_day_callback,
    cal_week_callback,
    meeting_detail_callback,
)
from donna_bot.state.machine import State


# ── Fixtures ────────────────────────────────────────────────────────────

SAMPLE_MEETINGS = [
    {
        "id": "meet-001",
        "subject": "Sprint Planning",
        "start": "10:00 AM",
        "duration": "60 min",
        "location": "Teams",
        "attendees": ["Satya", "Amy", "Mark"],
        "is_all_day": False,
        "join_url": "https://teams.microsoft.com/meet/1",
    },
    {
        "id": "meet-002",
        "subject": "1:1 with Manager",
        "start": "2:00 PM",
        "duration": "30 min",
        "location": "Room 42",
        "attendees": ["Boss"],
        "is_all_day": False,
        "join_url": "",
    },
]

SAMPLE_FOCUS = {
    "meeting_count": 2,
    "focus_hours": 5.5,
    "total_meeting_hours": 1.5,
}


def _make_update(chat_id: int = 496116833, text: str = "/cal") -> Update:
    """Build a fake Update with message."""
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
    """Build a fake Update with callback query."""
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


def _make_context(graph: AsyncMock | None = None) -> ContextTypes.DEFAULT_TYPE:
    """Build a fake context with bot_data."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    settings = MagicMock()
    settings.harvey_chat_id = 496116833

    ctx.bot_data = {
        "settings": settings,
        "graph": graph,
    }
    ctx.user_data = {}
    return ctx


# ── Unit Tests: Formatters ──────────────────────────────────────────────

class TestDayText:
    def test_renders_meetings(self):
        text = _format_day_text(SAMPLE_MEETINGS, SAMPLE_FOCUS)
        assert "TODAY" in text
        assert "Sprint Planning" in text
        assert "1:1 with Manager" in text
        assert "2 meetings" in text
        assert "focus" in text

    def test_renders_empty_day(self):
        focus = {"meeting_count": 0, "focus_hours": 8.0}
        text = _format_day_text([], focus)
        assert "No meetings" in text

    def test_shows_attendees(self):
        text = _format_day_text(SAMPLE_MEETINGS, SAMPLE_FOCUS)
        assert "Satya" in text

    def test_shows_location(self):
        text = _format_day_text(SAMPLE_MEETINGS, SAMPLE_FOCUS)
        assert "Teams" in text


class TestWeekText:
    def test_renders_meetings(self):
        text = _format_week_text(SAMPLE_MEETINGS)
        assert "THIS WEEK" in text
        assert "Sprint Planning" in text

    def test_renders_empty_week(self):
        text = _format_week_text([])
        assert "Empty week" in text


class TestDayKeyboard:
    def test_has_meeting_buttons(self):
        kb = _day_keyboard(SAMPLE_MEETINGS)
        buttons = kb.inline_keyboard
        # 2 meeting buttons + 1 controls row
        assert len(buttons) == 3

    def test_controls_row(self):
        kb = _day_keyboard(SAMPLE_MEETINGS)
        controls = kb.inline_keyboard[-1]
        labels = [b.text for b in controls]
        assert any("Week" in l for l in labels)
        assert any("Close" in l for l in labels)


class TestTalkingPoints:
    def test_standup(self):
        m = {"subject": "Daily Standup", "attendees": []}
        points = _generate_talking_points(m)
        assert any("yesterday" in p.lower() for p in points)

    def test_one_on_one(self):
        m = {"subject": "1:1 with Amy", "attendees": []}
        points = _generate_talking_points(m)
        assert any("sprint" in p.lower() or "career" in p.lower() for p in points)

    def test_large_meeting(self):
        m = {"subject": "All Hands", "attendees": list(range(10))}
        points = _generate_talking_points(m)
        assert any("Large meeting" in p for p in points)

    def test_generic_meeting(self):
        m = {"subject": "Catch Up", "attendees": []}
        points = _generate_talking_points(m)
        assert len(points) >= 1


# ── Handler Tests ───────────────────────────────────────────────────────

class TestCalCommand:
    @pytest.mark.asyncio
    async def test_no_graph_returns_end(self):
        update = _make_update()
        ctx = _make_context(graph=None)
        result = await cal_command(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_shows_day_view(self):
        graph = AsyncMock()
        update = _make_update()
        ctx = _make_context(graph=graph)

        with patch(
            "donna_bot.handlers.calendar.get_today",
            return_value=SAMPLE_MEETINGS,
        ), patch(
            "donna_bot.handlers.calendar.calc_focus_time",
            return_value=SAMPLE_FOCUS,
        ):
            result = await cal_command(update, ctx)

        assert result == State.CALENDAR_DAY
        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        assert "MarkdownV2" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_graph_error_returns_end(self):
        graph = AsyncMock()
        update = _make_update()
        ctx = _make_context(graph=graph)

        with patch(
            "donna_bot.handlers.calendar.get_today",
            side_effect=Exception("API error"),
        ):
            result = await cal_command(update, ctx)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_unauthorized_blocked(self):
        update = _make_update(chat_id=999)
        ctx = _make_context(graph=AsyncMock())
        result = await cal_command(update, ctx)
        assert result is None  # Silently blocked


class TestCalDayCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_callback_update("cal:close")
        ctx = _make_context(graph=AsyncMock())
        result = await cal_day_callback(update, ctx)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_week_view(self):
        update = _make_callback_update("cal:week")
        ctx = _make_context(graph=AsyncMock())

        with patch(
            "donna_bot.handlers.calendar.get_week",
            return_value=SAMPLE_MEETINGS,
        ):
            result = await cal_day_callback(update, ctx)

        assert result == State.CALENDAR_WEEK

    @pytest.mark.asyncio
    async def test_meeting_detail(self):
        update = _make_callback_update("cal:detail:meet-001")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["cal_meetings"] = SAMPLE_MEETINGS

        result = await cal_day_callback(update, ctx)
        assert result == State.MEETING_DETAIL

    @pytest.mark.asyncio
    async def test_meeting_not_found(self):
        update = _make_callback_update("cal:detail:nonexistent")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["cal_meetings"] = SAMPLE_MEETINGS

        result = await cal_day_callback(update, ctx)
        assert result == State.CALENDAR_DAY


class TestCalWeekCallback:
    @pytest.mark.asyncio
    async def test_today_returns_day(self):
        update = _make_callback_update("cal:today")
        ctx = _make_context(graph=AsyncMock())

        with patch(
            "donna_bot.handlers.calendar.get_today",
            return_value=SAMPLE_MEETINGS,
        ), patch(
            "donna_bot.handlers.calendar.calc_focus_time",
            return_value=SAMPLE_FOCUS,
        ):
            result = await cal_week_callback(update, ctx)

        assert result == State.CALENDAR_DAY

    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_callback_update("cal:close")
        ctx = _make_context(graph=AsyncMock())
        result = await cal_week_callback(update, ctx)
        assert result == ConversationHandler.END


class TestMeetingDetailCallback:
    @pytest.mark.asyncio
    async def test_back(self):
        update = _make_callback_update("cal:back")
        ctx = _make_context(graph=AsyncMock())

        with patch(
            "donna_bot.handlers.calendar.get_today",
            return_value=SAMPLE_MEETINGS,
        ), patch(
            "donna_bot.handlers.calendar.calc_focus_time",
            return_value=SAMPLE_FOCUS,
        ):
            result = await meeting_detail_callback(update, ctx)

        assert result == State.CALENDAR_DAY

    @pytest.mark.asyncio
    async def test_prep(self):
        update = _make_callback_update("cal:prep:meet-001")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["current_meeting"] = SAMPLE_MEETINGS[0]

        result = await meeting_detail_callback(update, ctx)
        assert result == State.MEETING_PREP

    @pytest.mark.asyncio
    async def test_prep_meeting_not_found(self):
        update = _make_callback_update("cal:prep:nonexistent")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["current_meeting"] = None
        ctx.user_data["cal_meetings"] = []

        result = await meeting_detail_callback(update, ctx)
        assert result == State.CALENDAR_DAY


class TestBuildConversation:
    def test_builds_handler(self):
        handler = build_calendar_conversation()
        assert handler is not None
        assert handler.name == "calendar_flow"
