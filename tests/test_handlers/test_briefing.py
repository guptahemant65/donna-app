"""Tests for briefing handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch



class TestBriefHandler:
    async def test_sends_progress_then_briefing(self) -> None:
        """Briefing handler should show progress → then briefing card."""
        from donna_bot.handlers.briefing import brief_handler

        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 496116833
        update.effective_user = MagicMock()
        update.effective_user.first_name = "Harvey"

        # reply_text returns a message object we can edit
        sent_msg = MagicMock()
        sent_msg.edit_text = AsyncMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock(return_value=sent_msg)

        context = MagicMock()
        context.bot_data = {
            "settings": MagicMock(harvey_chat_id=496116833),
        }

        # Mock graph client
        mock_graph = MagicMock()
        mock_graph.get = AsyncMock()
        context.bot_data["graph"] = mock_graph

        # Mock the graph module functions
        with (
            patch("donna_bot.handlers.briefing.get_profile", new_callable=AsyncMock) as mock_profile,
            patch("donna_bot.handlers.briefing.get_presence", new_callable=AsyncMock) as mock_presence,
            patch("donna_bot.handlers.briefing.get_today", new_callable=AsyncMock) as mock_today,
            patch("donna_bot.handlers.briefing.get_unread", new_callable=AsyncMock) as mock_unread,
        ):
            mock_profile.return_value = {"displayName": "Harvey", "mail": "h@ms.com"}
            mock_presence.return_value = {"availability": "Available"}
            mock_today.return_value = [
                {"subject": "Standup", "start": "10:00 AM", "duration": "15m"},
            ]
            mock_unread.return_value = [
                {"from": "Priya", "subject": "Design spec"},
            ]

            await brief_handler(update, context)

            # Should have sent initial progress message
            update.message.reply_text.assert_called_once()

            # Should have edited multiple times (progress steps + final card)
            assert sent_msg.edit_text.call_count >= 4

            # Final call should contain briefing content
            final_text = sent_msg.edit_text.call_args_list[-1][1].get(
                "text", sent_msg.edit_text.call_args_list[-1][0][0] if sent_msg.edit_text.call_args_list[-1][0] else ""
            )
            assert "MORNING BRIEFING" in final_text or "BRIEFING" in final_text

    async def test_handles_no_graph_client(self) -> None:
        from donna_bot.handlers.briefing import brief_handler

        update = MagicMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = 496116833
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {
            "settings": MagicMock(harvey_chat_id=496116833),
        }
        # No graph client

        await brief_handler(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "not configured" in call_text.lower()
