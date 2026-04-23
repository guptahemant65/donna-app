"""Tests for handlers/fallback.py — intent detection + routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from donna_bot.handlers.fallback import detect_intent, fallback_handler


# ── Unit Tests: detect_intent ───────────────────────────────────────────


class TestDetectIntent:
    # Email intents
    def test_check_emails(self):
        cmd, q = detect_intent("check my emails")
        assert cmd == "/email"

    def test_inbox(self):
        cmd, q = detect_intent("show inbox")
        assert cmd == "/email"

    def test_unread(self):
        cmd, q = detect_intent("any unread?")
        assert cmd == "/email"

    def test_mail(self):
        cmd, q = detect_intent("mail please")
        assert cmd == "/email"

    # Calendar intents
    def test_calendar(self):
        cmd, q = detect_intent("show my calendar")
        assert cmd == "/cal"

    def test_meetings_today(self):
        cmd, q = detect_intent("meetings today")
        assert cmd == "/cal"

    def test_my_day(self):
        cmd, q = detect_intent("what's on my day")
        assert cmd == "/cal"

    def test_schedule(self):
        cmd, q = detect_intent("show my schedule")
        assert cmd == "/cal"

    def test_whats_on_calendar(self):
        cmd, q = detect_intent("what's on my calendar")
        assert cmd == "/cal"

    # People intents
    def test_who_is(self):
        cmd, q = detect_intent("who is Alice Smith")
        assert cmd == "/who"
        assert q == "Alice Smith"

    def test_who_owns(self):
        cmd, q = detect_intent("who owns the auth service")
        assert cmd == "/who"
        assert q == "the auth service"

    def test_org_chart(self):
        cmd, q = detect_intent("show org chart")
        assert cmd == "/who"

    # Search intents
    def test_search_for(self):
        cmd, q = detect_intent("search for design doc")
        assert cmd == "/search"
        assert q == "design doc"

    def test_look_up(self):
        cmd, q = detect_intent("look up architecture review")
        assert cmd == "/search"
        assert q == "architecture review"

    def test_find_the_doc(self):
        cmd, q = detect_intent("find the FMV spec doc")
        assert cmd == "/search"
        assert q == "FMV spec"

    # Briefing intents
    def test_briefing(self):
        cmd, q = detect_intent("morning briefing")
        assert cmd == "/brief"

    def test_status(self):
        cmd, q = detect_intent("give me a status")
        assert cmd == "/brief"

    def test_hows_my_day(self):
        cmd, q = detect_intent("how's my day")
        assert cmd == "/cal"  # "my day" matches calendar pattern

    # Help intents
    def test_help(self):
        cmd, q = detect_intent("help please")
        assert cmd == "/help"

    def test_what_can_you_do(self):
        cmd, q = detect_intent("what can you do")
        assert cmd == "/help"

    # No match
    def test_no_match(self):
        cmd, q = detect_intent("supercalifragilistic")
        assert cmd == ""
        assert q == ""

    def test_empty_string(self):
        cmd, q = detect_intent("")
        assert cmd == ""

    # Case insensitivity
    def test_case_insensitive(self):
        cmd, q = detect_intent("CHECK MY EMAILS")
        assert cmd == "/email"


# ── Handler Tests ───────────────────────────────────────────────────────


def _make_update(text=""):
    update = MagicMock()
    chat = MagicMock()
    chat.id = 496116833
    update.effective_chat = chat
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.from_user = MagicMock()
    update.message.from_user.id = 496116833
    return update


def _make_context():
    context = MagicMock()
    context.bot_data = {}
    settings = MagicMock()
    settings.harvey_chat_id = 496116833
    context.bot_data["settings"] = settings
    return context


class TestFallbackHandler:
    @pytest.mark.asyncio
    async def test_detected_intent_shows_suggestion(self):
        update = _make_update("check my emails")
        context = _make_context()
        await fallback_handler(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/email" in text

    @pytest.mark.asyncio
    async def test_no_match_shows_suggestions(self):
        update = _make_update("xyzzy plugh")
        context = _make_context()
        await fallback_handler(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/brief" in text
        assert "/mail" in text
        assert "/cal" in text
        assert "/who" in text
        assert "/search" in text

    @pytest.mark.asyncio
    async def test_search_with_query(self):
        update = _make_update("search for design review")
        context = _make_context()
        await fallback_handler(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/search" in text
        assert "design review" in text

    @pytest.mark.asyncio
    async def test_who_with_name(self):
        update = _make_update("who is Alice")
        context = _make_context()
        await fallback_handler(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/who Alice" in text
