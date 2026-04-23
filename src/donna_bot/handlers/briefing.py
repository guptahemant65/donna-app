"""Morning briefing handler — the crown jewel."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from donna_bot.formatters.cards import format_briefing_card
from donna_bot.formatters.keyboards import briefing_keyboard
from donna_bot.formatters.progress import progress_message
from donna_bot.graph.calendar import calc_focus_time, get_today
from donna_bot.graph.mail import get_unread
from donna_bot.graph.me import get_presence, get_profile
from donna_bot.middleware.security import harvey_only

logger = logging.getLogger(__name__)


@harvey_only
async def brief_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /brief — full morning briefing with live progress."""
    graph = context.bot_data.get("graph")
    if not graph:
        await update.message.reply_text("Graph client not configured.")
        return

    # Step 1: Send progress message
    msg = await update.message.reply_text(
        progress_message("Connecting to Microsoft Graph...", 10),
        parse_mode="MarkdownV2",
    )

    try:
        # Step 2: Fetch profile + presence
        await msg.edit_text(
            progress_message("Reading your profile...", 25),
            parse_mode="MarkdownV2",
        )
        profile = await get_profile(graph)
        presence = await get_presence(graph)

        # Step 3: Fetch calendar
        await msg.edit_text(
            progress_message("Scanning calendar...", 50),
            parse_mode="MarkdownV2",
        )
        meetings = await get_today(graph)
        focus = calc_focus_time(meetings)

        # Step 4: Fetch emails
        await msg.edit_text(
            progress_message("Triaging inbox...", 75),
            parse_mode="MarkdownV2",
        )
        emails = await get_unread(graph, top=5)

        # Step 5: Compose briefing card
        await msg.edit_text(
            progress_message("Brewing your briefing...", 95),
            parse_mode="MarkdownV2",
        )

        # Build meeting summaries for card
        meeting_summaries = [
            {"subject": m["subject"], "start": m["start"], "duration": m["duration"]}
            for m in meetings[:5]
        ]

        # Build email summaries for card
        email_summaries = [
            {"from": e["from"], "subject": e["subject"]}
            for e in emails[:5]
        ]

        sprint_data = {"done": 0, "total": 0}  # TODO: wire to ADO/GitHub

        card = format_briefing_card(
            incidents=[],  # TODO: wire to IcM
            emails=email_summaries,
            meetings=meeting_summaries,
            sprint=sprint_data,
        )

        kb = briefing_keyboard(
            email_count=len(emails),
            meeting_count=len(meetings),
        )

        # Step 6: Replace progress with actual briefing
        await msg.edit_text(
            card,
            parse_mode="MarkdownV2",
            reply_markup=kb,
        )

        logger.info(
            "Briefing delivered: %d emails, %d meetings, %.1fh focus",
            len(emails),
            len(meetings),
            focus["focus_hours"],
        )

    except Exception:
        logger.exception("Briefing failed")
        await msg.edit_text(
            "Something went wrong brewing your briefing\\. Try again\\?",
            parse_mode="MarkdownV2",
        )
