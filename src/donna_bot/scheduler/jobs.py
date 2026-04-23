"""Scheduled jobs — proactive intelligence."""

from __future__ import annotations

import logging
from datetime import time, timezone, timedelta

from telegram.ext import Application

from donna_bot.config import Settings

logger = logging.getLogger(__name__)

# IST timezone
_IST = timezone(timedelta(hours=5, minutes=30))


def schedule_morning_briefing(app: Application, settings: Settings) -> None:
    """Schedule the morning briefing job at configured time."""
    if not settings.feature_briefing:
        logger.info("Morning briefing disabled — skipping schedule")
        return

    briefing_time = time(
        hour=settings.briefing_hour,
        minute=settings.briefing_minute,
        tzinfo=_IST,
    )

    app.job_queue.run_daily(
        _send_morning_briefing,
        time=briefing_time,
        chat_id=settings.harvey_chat_id,
        name="morning_briefing",
        data={"settings": settings},
    )

    logger.info(
        "Morning briefing scheduled at %02d:%02d IST",
        settings.briefing_hour,
        settings.briefing_minute,
    )


def schedule_eod_summary(app: Application, settings: Settings) -> None:
    """Schedule end-of-day summary at configured time."""
    if not settings.feature_briefing:
        return

    eod_time = time(
        hour=settings.eod_hour,
        minute=settings.eod_minute,
        tzinfo=_IST,
    )

    app.job_queue.run_daily(
        _send_eod_summary,
        time=eod_time,
        chat_id=settings.harvey_chat_id,
        name="eod_summary",
        data={"settings": settings},
    )

    logger.info(
        "EOD summary scheduled at %02d:%02d IST",
        settings.eod_hour,
        settings.eod_minute,
    )


async def _send_morning_briefing(context) -> None:
    """Job callback: send morning briefing to Harvey."""
    from donna_bot.formatters.cards import format_briefing_card
    from donna_bot.formatters.keyboards import briefing_keyboard
    from donna_bot.graph.calendar import get_today
    from donna_bot.graph.mail import get_unread
    from donna_bot.graph.me import get_profile

    graph = context.bot_data.get("graph")
    if not graph:
        logger.error("No graph client in bot_data — can't send briefing")
        return

    chat_id = context.job.chat_id

    try:
        profile = await get_profile(graph)
        meetings = await get_today(graph)
        emails = await get_unread(graph, top=5)

        meeting_summaries = [
            {"subject": m["subject"], "start": m["start"], "duration": m["duration"]}
            for m in meetings[:5]
        ]
        email_summaries = [
            {"from": e["from"], "subject": e["subject"]}
            for e in emails[:5]
        ]

        card = format_briefing_card(
            incidents=[],
            emails=email_summaries,
            meetings=meeting_summaries,
            sprint={"done": 0, "total": 0},
        )

        kb = briefing_keyboard(
            email_count=len(emails),
            meeting_count=len(meetings),
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=card,
            parse_mode="MarkdownV2",
            reply_markup=kb,
        )
        logger.info("Morning briefing sent to chat_id=%s", chat_id)

    except Exception:
        logger.exception("Failed to send morning briefing")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Morning briefing failed\\. I'll try again in 5 minutes\\.",
            parse_mode="MarkdownV2",
        )


async def _send_eod_summary(context) -> None:
    """Job callback: send end-of-day summary."""
    chat_id = context.job.chat_id
    # TODO: Implement full EOD summary with day's activity
    await context.bot.send_message(
        chat_id=chat_id,
        text="Good evening, boss\\. EOD summary coming soon\\.",
        parse_mode="MarkdownV2",
    )
