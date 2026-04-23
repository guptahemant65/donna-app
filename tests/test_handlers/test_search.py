"""Tests for handlers/search.py — search handler + formatters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donna_bot.handlers.search import (
    _format_search_results,
    _results_keyboard,
    build_search_conversation,
    refine_query,
    results_callback,
    search_command,
)
from donna_bot.state.machine import State


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_update(text="", args=None, is_callback=False, callback_data=""):
    update = MagicMock()
    chat = MagicMock()
    chat.id = 496116833
    update.effective_chat = chat

    if is_callback:
        update.callback_query = MagicMock()
        update.callback_query.data = callback_data
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.message = None
    else:
        update.message = MagicMock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = 496116833
        update.callback_query = None

    return update


def _make_context(has_graph=True, args=None):
    context = MagicMock()
    context.args = args or []
    context.user_data = {}
    context.bot_data = {}

    if has_graph:
        context.bot_data["graph"] = MagicMock()

    settings = MagicMock()
    settings.harvey_chat_id = 496116833
    context.bot_data["settings"] = settings

    return context


SAMPLE_RESULTS = {
    "emails": [
        {
            "type": "email",
            "id": "m1",
            "subject": "Design Review",
            "from": "Alice",
            "date": "2025-01-15",
            "preview": "Please review",
            "webLink": "https://outlook.com/m1",
            "summary": "design review summary",
            "rank": 1,
        },
    ],
    "files": [
        {
            "type": "file",
            "id": "f1",
            "name": "Architecture.docx",
            "webUrl": "https://sp.com/f1",
            "lastModified": "2025-01-10",
            "size": 1024,
            "createdBy": "Bob",
            "summary": "",
            "rank": 1,
        },
    ],
}


# ── Formatter Tests ─────────────────────────────────────────────────────


class TestFormatSearchResults:
    def test_with_results(self):
        text = _format_search_results(SAMPLE_RESULTS, "design doc")
        assert "SEARCH" in text
        assert "EMAILS" in text
        assert "FILES" in text
        assert "Design Review" in text
        assert "Architecture" in text

    def test_empty_results(self):
        text = _format_search_results({}, "nothing")
        assert "Nothing found" in text

    def test_long_results_truncated(self):
        many = {
            "emails": [
                {"type": "email", "id": f"m{i}", "subject": f"Email {i}",
                 "from": "X", "date": "", "preview": "", "webLink": "",
                 "summary": "", "rank": i}
                for i in range(10)
            ],
        }
        text = _format_search_results(many, "test")
        assert "and 5 more" in text


class TestResultsKeyboard:
    def test_has_close_button(self):
        kb = _results_keyboard(SAMPLE_RESULTS)
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "search:close" in all_data

    def test_has_refine_button(self):
        kb = _results_keyboard(SAMPLE_RESULTS)
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        assert "search:refine" in all_data

    def test_url_buttons(self):
        kb = _results_keyboard(SAMPLE_RESULTS)
        urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
        assert len(urls) >= 1

    def test_empty_results(self):
        kb = _results_keyboard({})
        # Should still have close/refine row
        assert len(kb.inline_keyboard) >= 1


# ── Handler Tests ───────────────────────────────────────────────────────


class TestSearchCommand:
    @pytest.mark.asyncio
    async def test_no_query_shows_usage(self):
        update = _make_update(text="/search")
        context = _make_context(args=[])
        result = await search_command(update, context)
        update.message.reply_text.assert_called_once()
        assert "Usage" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_no_graph_shows_error(self):
        update = _make_update(text="/search test")
        context = _make_context(has_graph=False, args=["test"])
        result = await search_command(update, context)
        update.message.reply_text.assert_called_once()
        assert "not configured" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_successful_search(self):
        update = _make_update(text="/search design doc")
        context = _make_context(args=["design", "doc"])

        with patch("donna_bot.handlers.search.search_m365", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = SAMPLE_RESULTS
            result = await search_command(update, context)

        assert result == State.SEARCH_RESULTS
        update.message.reply_text.assert_called_once()
        assert context.user_data["search_query"] == "design doc"

    @pytest.mark.asyncio
    async def test_search_error(self):
        update = _make_update(text="/search fail")
        context = _make_context(args=["fail"])

        with patch("donna_bot.handlers.search.search_m365", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("API error")
            result = await search_command(update, context)

        # Should end conversation on error
        assert result == -1  # ConversationHandler.END


class TestResultsCallback:
    @pytest.mark.asyncio
    async def test_close(self):
        update = _make_update(is_callback=True, callback_data="search:close")
        context = _make_context()
        result = await results_callback(update, context)
        assert result == -1  # END

    @pytest.mark.asyncio
    async def test_refine(self):
        update = _make_update(is_callback=True, callback_data="search:refine")
        context = _make_context()
        result = await results_callback(update, context)
        assert result == State.SEARCH_QUERY


class TestRefineQuery:
    @pytest.mark.asyncio
    async def test_empty_query(self):
        update = _make_update(text="")
        context = _make_context()
        result = await refine_query(update, context)
        assert result == State.SEARCH_QUERY

    @pytest.mark.asyncio
    async def test_new_query(self):
        update = _make_update(text="new query")
        context = _make_context()

        with patch("donna_bot.handlers.search.search_m365", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = SAMPLE_RESULTS
            result = await refine_query(update, context)

        assert result == State.SEARCH_RESULTS


class TestBuildConversation:
    def test_returns_handler(self):
        handler = build_search_conversation()
        assert handler is not None
        assert handler.name == "search_flow"
