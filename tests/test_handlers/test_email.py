"""Tests for email ConversationHandler — every state transition."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import CallbackQuery, Chat, Message, Update, User
from telegram.ext import ContextTypes, ConversationHandler

from donna_bot.handlers.email import (
    _format_email_list_text,
    _enriched_email_list_keyboard,
    build_email_conversation,
    cancel_compose,
    compose_confirm_callback,
    compose_text_handler,
    email_action_callback,
    email_command,
    email_list_callback,
)
from donna_bot.state.machine import State


# ── Fixtures ────────────────────────────────────────────────────────────

SAMPLE_EMAILS = [
    {
        "id": "AAA111",
        "subject": "Sprint Planning",
        "from": "Satya Nadella",
        "from_email": "satya@microsoft.com",
        "date": "Apr 23, 09:00 AM",
        "preview": "Let's discuss the roadmap...",
        "isRead": False,
        "hasAttachments": False,
        "importance": "high",
    },
    {
        "id": "BBB222",
        "subject": "Build Failed",
        "from": "Azure DevOps",
        "from_email": "noreply@dev.azure.com",
        "date": "Apr 23, 08:30 AM",
        "preview": "Pipeline ci-main failed...",
        "isRead": True,
        "hasAttachments": True,
        "importance": "normal",
    },
]

SAMPLE_EMAIL_FULL = {
    "id": "AAA111",
    "subject": "Sprint Planning",
    "from": "Satya Nadella",
    "from_email": "satya@microsoft.com",
    "to": ["Harvey Specter"],
    "date": "Apr 23, 09:00 AM",
    "body": "Let's discuss the roadmap for Q3. Key items: 1. FMV launch, 2. Agent infra.",
    "preview": "Let's discuss the roadmap...",
    "isRead": False,
    "hasAttachments": False,
    "importance": "high",
    "conversationId": "conv-001",
}


def _make_update(chat_id: int = 496116833, text: str = "/email") -> Update:
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


def _make_callback_update(
    data: str, chat_id: int = 496116833,
) -> Update:
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


def _make_context(
    settings: MagicMock | None = None,
    graph: AsyncMock | None = None,
) -> ContextTypes.DEFAULT_TYPE:
    """Build a fake context with bot_data."""
    ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    if settings is None:
        settings = MagicMock()
        settings.harvey_chat_id = 496116833

    ctx.bot_data = {
        "settings": settings,
        "graph": graph,
    }
    ctx.user_data = {}
    return ctx


# ── Unit Tests: Formatters ──────────────────────────────────────────────

class TestEmailListText:
    def test_renders_emails_with_unread_markers(self):
        text = _format_email_list_text(SAMPLE_EMAILS, page=1, total=2, unread_count=1)
        assert "INBOX" in text
        assert "page 1" in text
        assert "Satya Nadella" in text
        assert "Sprint Planning" in text

    def test_renders_empty_inbox(self):
        text = _format_email_list_text([], page=1, total=0, unread_count=0)
        assert "Inbox zero" in text

    def test_renders_page_number(self):
        text = _format_email_list_text(SAMPLE_EMAILS, page=3, total=25)
        assert "page 3" in text


class TestEmailListKeyboard:
    def test_builds_keyboard_with_email_buttons(self):
        kb = _enriched_email_list_keyboard(SAMPLE_EMAILS, page=1, total=10)
        # 2 email buttons + 1 nav row + 1 close row = 4 rows
        assert len(kb.inline_keyboard) == 4
        # First email button has the sender
        assert "Satya" in kb.inline_keyboard[0][0].text

    def test_first_page_no_prev_button(self):
        kb = _enriched_email_list_keyboard(SAMPLE_EMAILS, page=1, total=10)
        nav_row = kb.inline_keyboard[2]  # nav row
        labels = [b.text for b in nav_row]
        assert not any("Prev" in l for l in labels)
        assert any("Next" in l for l in labels)

    def test_last_page_no_next_button(self):
        kb = _enriched_email_list_keyboard(SAMPLE_EMAILS, page=2, total=10)
        nav_row = kb.inline_keyboard[2]
        labels = [b.text for b in nav_row]
        assert any("Prev" in l for l in labels)
        assert not any("Next" in l for l in labels)


# ── Handler Tests ───────────────────────────────────────────────────────

class TestEmailCommand:
    @pytest.mark.asyncio
    async def test_shows_inbox_on_command(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.get_inbox", new_callable=AsyncMock) as mock_inbox, \
             patch("donna_bot.handlers.email.get_unread", new_callable=AsyncMock) as mock_unread:
            mock_inbox.return_value = {"emails": SAMPLE_EMAILS, "total": 2}
            mock_unread.return_value = [SAMPLE_EMAILS[0]]

            update = _make_update()
            ctx = _make_context(graph=graph)

            result = await email_command(update, ctx)

            assert result == State.EMAIL_LIST
            update.message.reply_text.assert_called_once()
            call_text = update.message.reply_text.call_args[0][0]
            assert "INBOX" in call_text

    @pytest.mark.asyncio
    async def test_no_graph_returns_end(self):
        update = _make_update()
        ctx = _make_context(graph=None)

        result = await email_command(update, ctx)

        assert result == ConversationHandler.END


class TestEmailListCallback:
    @pytest.mark.asyncio
    async def test_pagination_fetches_next_page(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.get_inbox", new_callable=AsyncMock) as mock_inbox, \
             patch("donna_bot.handlers.email.get_unread", new_callable=AsyncMock) as mock_unread:
            mock_inbox.return_value = {"emails": SAMPLE_EMAILS, "total": 15}
            mock_unread.return_value = []

            update = _make_callback_update("email:page:2")
            ctx = _make_context(graph=graph)

            result = await email_list_callback(update, ctx)

            assert result == State.EMAIL_LIST
            mock_inbox.assert_called_once_with(graph, top=5, skip=5)

    @pytest.mark.asyncio
    async def test_read_email_shows_detail(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.get_email", new_callable=AsyncMock) as mock_get, \
             patch("donna_bot.handlers.email.mark_read", new_callable=AsyncMock):
            mock_get.return_value = SAMPLE_EMAIL_FULL

            update = _make_callback_update("email:read:AAA111")
            ctx = _make_context(graph=graph)

            result = await email_list_callback(update, ctx)

            assert result == State.EMAIL_READ
            mock_get.assert_called_once_with(graph, "AAA111")

    @pytest.mark.asyncio
    async def test_close_ends_conversation(self):
        update = _make_callback_update("email:close")
        ctx = _make_context(graph=AsyncMock())

        result = await email_list_callback(update, ctx)

        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_noop_stays_on_list(self):
        update = _make_callback_update("noop")
        ctx = _make_context(graph=AsyncMock())

        result = await email_list_callback(update, ctx)

        assert result == State.EMAIL_LIST


class TestEmailActionCallback:
    @pytest.mark.asyncio
    async def test_back_returns_to_list(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.get_inbox", new_callable=AsyncMock) as mock_inbox, \
             patch("donna_bot.handlers.email.get_unread", new_callable=AsyncMock):
            mock_inbox.return_value = {"emails": SAMPLE_EMAILS, "total": 2}

            update = _make_callback_update("email:back")
            ctx = _make_context(graph=graph)
            ctx.user_data["email_page"] = 1

            result = await email_action_callback(update, ctx)

            assert result == State.EMAIL_LIST

    @pytest.mark.asyncio
    async def test_archive_removes_and_refreshes(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.archive", new_callable=AsyncMock) as mock_archive, \
             patch("donna_bot.handlers.email.get_inbox", new_callable=AsyncMock) as mock_inbox, \
             patch("donna_bot.handlers.email.get_unread", new_callable=AsyncMock):
            mock_inbox.return_value = {"emails": [SAMPLE_EMAILS[1]], "total": 1}

            update = _make_callback_update("email:archive:AAA111")
            ctx = _make_context(graph=graph)
            ctx.user_data["email_page"] = 1

            result = await email_action_callback(update, ctx)

            assert result == State.EMAIL_LIST
            mock_archive.assert_called_once_with(graph, "AAA111")

    @pytest.mark.asyncio
    async def test_reply_enters_compose(self):
        update = _make_callback_update("email:reply:AAA111")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["current_email"] = SAMPLE_EMAIL_FULL

        result = await email_action_callback(update, ctx)

        assert result == State.EMAIL_COMPOSE
        assert ctx.user_data["reply_to_id"] == "AAA111"

    @pytest.mark.asyncio
    async def test_forward_stub(self):
        update = _make_callback_update("email:fwd:AAA111")
        ctx = _make_context(graph=AsyncMock())

        result = await email_action_callback(update, ctx)

        assert result == State.EMAIL_READ


class TestComposeFlow:
    @pytest.mark.asyncio
    async def test_text_stages_reply(self):
        update = _make_update(text="Thanks, sounds good!")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["reply_to_subject"] = "Sprint Planning"
        ctx.user_data["reply_to_sender"] = "Satya Nadella"

        result = await compose_text_handler(update, ctx)

        assert result == State.EMAIL_COMPOSE
        assert ctx.user_data["reply_draft"] == "Thanks, sounds good!"
        # Verify confirm keyboard was sent
        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        assert call_kwargs[1].get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_empty_text_rejected(self):
        update = _make_update(text="   ")
        ctx = _make_context(graph=AsyncMock())

        result = await compose_text_handler(update, ctx)

        assert result == State.EMAIL_COMPOSE
        assert "reply_draft" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_confirm_yes_sends_reply(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.reply", new_callable=AsyncMock) as mock_reply:
            update = _make_callback_update("confirm:yes:reply")
            ctx = _make_context(graph=graph)
            ctx.user_data["reply_to_id"] = "AAA111"
            ctx.user_data["reply_draft"] = "Sounds good!"
            ctx.user_data["reply_to_sender"] = "Satya"
            ctx.user_data["reply_to_subject"] = "Sprint"

            result = await compose_confirm_callback(update, ctx)

            assert result == ConversationHandler.END
            mock_reply.assert_called_once_with(graph, "AAA111", "Sounds good!")
            # Verify compose state cleaned up
            assert "reply_draft" not in ctx.user_data
            assert "reply_to_id" not in ctx.user_data

    @pytest.mark.asyncio
    async def test_confirm_no_returns_to_email(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.get_email", new_callable=AsyncMock) as mock_get, \
             patch("donna_bot.handlers.email.mark_read", new_callable=AsyncMock):
            mock_get.return_value = SAMPLE_EMAIL_FULL

            update = _make_callback_update("confirm:no:reply")
            ctx = _make_context(graph=graph)
            ctx.user_data["reply_to_id"] = "AAA111"

            result = await compose_confirm_callback(update, ctx)

            assert result == State.EMAIL_READ

    @pytest.mark.asyncio
    async def test_cancel_command_exits(self):
        update = _make_update(text="/cancel")
        ctx = _make_context(graph=AsyncMock())
        ctx.user_data["reply_to_id"] = "AAA111"
        ctx.user_data["reply_draft"] = "draft text"

        result = await cancel_compose(update, ctx)

        assert result == ConversationHandler.END
        assert "reply_draft" not in ctx.user_data
        assert "reply_to_id" not in ctx.user_data


class TestConversationHandlerFactory:
    def test_builds_valid_handler(self):
        handler = build_email_conversation()
        assert isinstance(handler, ConversationHandler)
        assert handler.name == "email_flow"
        # Has all three states
        assert State.EMAIL_LIST in handler.states
        assert State.EMAIL_READ in handler.states
        assert State.EMAIL_COMPOSE in handler.states
        # Two entry points: /email and /mail
        assert len(handler.entry_points) == 2


class TestReplyFailure:
    @pytest.mark.asyncio
    async def test_send_failure_shows_error(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.reply", new_callable=AsyncMock) as mock_reply:
            mock_reply.side_effect = Exception("Network error")

            update = _make_callback_update("confirm:yes:reply")
            ctx = _make_context(graph=graph)
            ctx.user_data["reply_to_id"] = "AAA111"
            ctx.user_data["reply_draft"] = "test"
            ctx.user_data["reply_to_sender"] = "test"
            ctx.user_data["reply_to_subject"] = "test"

            result = await compose_confirm_callback(update, ctx)

            assert result == ConversationHandler.END
            edit_text = update.callback_query.edit_message_text.call_args[0][0]
            assert "Failed" in edit_text


class TestArchiveFailure:
    @pytest.mark.asyncio
    async def test_archive_failure_stays_on_read(self):
        graph = AsyncMock()
        with patch("donna_bot.handlers.email.archive", new_callable=AsyncMock) as mock_archive:
            mock_archive.side_effect = Exception("Forbidden")

            update = _make_callback_update("email:archive:AAA111")
            ctx = _make_context(graph=graph)
            ctx.user_data["email_page"] = 1

            result = await email_action_callback(update, ctx)

            assert result == State.EMAIL_READ
            update.callback_query.answer.assert_called()
