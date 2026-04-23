"""Calendar Intelligence — day/week view, meeting detail, meeting prep.

ConversationHandler flow:
  /cal → CALENDAR_DAY
    ↕ tap meeting → MEETING_DETAIL
      ↕ "prep" → MEETING_PREP (auto-compose context card)
    ↕ "week" → CALENDAR_WEEK
    ↕ "close" → END

Meeting prep auto-scheduler:
  On /brief or bot start, scan today's calendar and schedule
  prep notifications for each meeting at T-5 minutes.
"""

from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from donna_bot.formatters.cards import format_meeting_card
from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_italic, md2_separator
from donna_bot.graph.calendar import calc_focus_time, get_today, get_week
from donna_bot.graph.client import GraphClient
from donna_bot.middleware.security import harvey_only
from donna_bot.state.machine import State

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_graph(context: ContextTypes.DEFAULT_TYPE) -> GraphClient | None:
    return context.bot_data.get("graph")


def _format_day_text(meetings: list[dict[str, Any]], focus: dict[str, Any]) -> str:
    """Format today's calendar as a text card."""
    lines = [
        md2_header(),
        f"📅 {md2_bold('TODAY')}",
        md2_italic(
            f"{focus['meeting_count']} meetings · "
            f"{focus['focus_hours']}h focus time"
        ),
        "",
    ]

    if not meetings:
        lines.append(md2("No meetings today. Pure focus time."))
    else:
        for m in meetings:
            if m.get("is_all_day"):
                time_str = "All day"
            else:
                time_str = m.get("start", "?")

            subject = md2(m.get("subject", "(No subject)")[:40])
            duration = md2(m.get("duration", ""))
            location = m.get("location", "")

            line = f"  {md2_bold(time_str)}  {subject}"
            if duration:
                line += f" {md2_italic('(' + m.get('duration', '') + ')')}"
            lines.append(line)

            if location:
                lines.append(f"    📍 {md2(location[:30])}")

            # Attendee count
            attendees = m.get("attendees", [])
            if attendees:
                count = len(attendees)
                first_two = ", ".join(a[:15] for a in attendees[:2])
                att_text = md2(first_two)
                if count > 2:
                    att_text += f" {md2_italic('+' + str(count - 2) + ' more')}"
                lines.append(f"    👥 {att_text}")

            lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _format_week_text(meetings: list[dict[str, Any]]) -> str:
    """Format week view grouped by day."""

    lines = [
        md2_header(),
        f"📅 {md2_bold('THIS WEEK')}",
        "",
    ]

    if not meetings:
        lines.append(md2("Empty week ahead. Suspicious."))
        lines.append(md2_separator())
        return "\n".join(lines)

    # Show count per day hint and flat list
    lines.append(md2_italic(f"{len(meetings)} meetings this week"))
    lines.append("")

    for m in meetings[:20]:
        subject = md2(m.get("subject", "(No subject)")[:35])
        start = md2(m.get("start", "?"))
        lines.append(f"  {md2_bold(start)} {subject} {md2_italic('(' + m.get('duration', '') + ')')}")

    if len(meetings) > 20:
        lines.append(f"  {md2_italic('... and ' + str(len(meetings) - 20) + ' more')}")

    lines.append("")
    lines.append(md2_separator())
    return "\n".join(lines)


def _day_keyboard(meetings: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build keyboard for day view — meeting buttons + controls."""
    buttons = []

    for m in meetings[:8]:
        subject = m.get("subject", "Meeting")[:25]
        start = m.get("start", "?")
        label = f"{start} — {subject}"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"cal:detail:{m.get('id', '')}")
        ])

    # Controls
    controls = [
        InlineKeyboardButton("📊 Week View", callback_data="cal:week"),
        InlineKeyboardButton("✕ Close", callback_data="cal:close"),
    ]
    buttons.append(controls)

    return InlineKeyboardMarkup(buttons)


def _week_keyboard() -> InlineKeyboardMarkup:
    """Week view controls."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("◀ Today", callback_data="cal:today"),
            InlineKeyboardButton("✕ Close", callback_data="cal:close"),
        ],
    ])


def _meeting_detail_keyboard(meeting: dict[str, Any]) -> InlineKeyboardMarkup:
    """Meeting detail actions."""
    meeting_id = meeting.get("id", "")
    join_url = meeting.get("join_url", "")

    row1 = [
        InlineKeyboardButton("📋 Prep", callback_data=f"cal:prep:{meeting_id}"),
    ]
    if join_url:
        row1.append(InlineKeyboardButton("🔗 Join", url=join_url))

    return InlineKeyboardMarkup([
        row1,
        [InlineKeyboardButton("◀ Back", callback_data="cal:back")],
    ])


# ── Handlers ────────────────────────────────────────────────────────────

@harvey_only
async def cal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cal — show today's calendar."""
    graph = _get_graph(context)
    if not graph:
        await update.message.reply_text(
            "Graph client not configured\\.",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    return await _show_day(update, context, edit=False)


async def _show_day(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit: bool = True,
) -> int:
    """Fetch and display today's calendar."""
    graph = _get_graph(context)

    try:
        meetings = await get_today(graph)
        focus = calc_focus_time(meetings)
    except Exception:
        logger.exception("Failed to fetch calendar")
        error = f"{md2_header()}\n\n{md2('Failed to load calendar.')}"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(error, parse_mode="MarkdownV2")
        else:
            await update.message.reply_text(error, parse_mode="MarkdownV2")
        return ConversationHandler.END

    context.user_data["cal_meetings"] = meetings

    text = _format_day_text(meetings, focus)
    kb = _day_keyboard(meetings)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=kb,
        )

    return State.CALENDAR_DAY


@harvey_only
async def cal_day_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle day view callbacks: detail, week, close."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "cal:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Calendar closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "cal:week":
        return await _show_week(update, context)

    if data.startswith("cal:detail:"):
        meeting_id = data.replace("cal:detail:", "")
        return await _show_meeting_detail(update, context, meeting_id)

    return State.CALENDAR_DAY


async def _show_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show week calendar view."""
    graph = _get_graph(context)

    try:
        meetings = await get_week(graph)
    except Exception:
        logger.exception("Failed to fetch week calendar")
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Failed to load week view.')}",
            parse_mode="MarkdownV2",
        )
        return State.CALENDAR_DAY

    text = _format_week_text(meetings)
    kb = _week_keyboard()

    await update.callback_query.edit_message_text(
        text, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.CALENDAR_WEEK


async def _show_meeting_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    meeting_id: str,
) -> int:
    """Show detail for a specific meeting."""
    meetings = context.user_data.get("cal_meetings", [])
    meeting = next((m for m in meetings if m.get("id") == meeting_id), None)

    if not meeting:
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Meeting not found.')}",
            parse_mode="MarkdownV2",
        )
        return State.CALENDAR_DAY

    context.user_data["current_meeting"] = meeting

    card = format_meeting_card(
        subject=meeting.get("subject", "Meeting"),
        time=meeting.get("start", "?"),
        duration=meeting.get("duration", ""),
        location=meeting.get("location", ""),
        attendees=meeting.get("attendees", []),
        join_url=meeting.get("join_url", ""),
    )
    kb = _meeting_detail_keyboard(meeting)

    await update.callback_query.edit_message_text(
        card, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.MEETING_DETAIL


@harvey_only
async def cal_week_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle week view callbacks: today, close."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "cal:close":
        await query.edit_message_text(
            f"{md2_header()}\n\n{md2('Calendar closed.')}",
            parse_mode="MarkdownV2",
        )
        return ConversationHandler.END

    if data == "cal:today":
        return await _show_day(update, context, edit=True)

    return State.CALENDAR_WEEK


@harvey_only
async def meeting_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle meeting detail callbacks: prep, back."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "cal:back":
        return await _show_day(update, context, edit=True)

    if data.startswith("cal:prep:"):
        meeting_id = data.replace("cal:prep:", "")
        return await _show_prep(update, context, meeting_id)

    return State.MEETING_DETAIL


async def _show_prep(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    meeting_id: str,
) -> int:
    """Generate and show meeting prep card."""
    meeting = context.user_data.get("current_meeting", {})

    if not meeting or meeting.get("id") != meeting_id:
        # Try to find in cached meetings
        meetings = context.user_data.get("cal_meetings", [])
        meeting = next((m for m in meetings if m.get("id") == meeting_id), {})

    if not meeting:
        await update.callback_query.edit_message_text(
            f"{md2_header()}\n\n{md2('Meeting not found for prep.')}",
            parse_mode="MarkdownV2",
        )
        return State.CALENDAR_DAY

    # Build prep card with context
    attendees = meeting.get("attendees", [])
    subject = meeting.get("subject", "Meeting")

    # Generate talking points based on meeting metadata
    talking_points = _generate_talking_points(meeting)

    card = format_meeting_card(
        subject=subject,
        time=meeting.get("start", "?"),
        duration=meeting.get("duration", ""),
        location=meeting.get("location", ""),
        attendees=attendees,
        context=f"You have {len(attendees)} attendees in this meeting.",
        talking_points=talking_points,
        join_url=meeting.get("join_url", ""),
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀ Back to meeting", callback_data="cal:back")],
    ])

    await update.callback_query.edit_message_text(
        card, parse_mode="MarkdownV2", reply_markup=kb,
    )

    return State.MEETING_PREP


def _generate_talking_points(meeting: dict[str, Any]) -> list[str]:
    """Generate basic talking points from meeting metadata.

    In future, this will use Graph search to pull relevant
    emails, documents, and previous meeting notes.
    """
    subject = meeting.get("subject", "").lower()
    attendees = meeting.get("attendees", [])
    points = []

    # Heuristic talking points based on meeting subject
    if "standup" in subject or "stand-up" in subject:
        points.extend([
            "What did you accomplish yesterday?",
            "What are you working on today?",
            "Any blockers?",
        ])
    elif "1:1" in subject or "one on one" in subject or "1-1" in subject:
        points.extend([
            "Review current sprint progress",
            "Discuss any blockers or concerns",
            "Career development check-in",
        ])
    elif "review" in subject:
        points.extend([
            "Review the changes/proposal",
            "Note any concerns or suggestions",
            "Agree on next steps",
        ])
    elif "planning" in subject or "sprint" in subject:
        points.extend([
            "Review backlog priorities",
            "Estimate upcoming work",
            "Identify dependencies",
        ])
    else:
        points.extend([
            f"Discuss {meeting.get('subject', 'agenda items')}",
            "Note any action items",
        ])

    if len(attendees) > 5:
        points.append(f"Large meeting ({len(attendees)} attendees) — be concise")

    return points


# ── Meeting Prep Auto-Scheduler ─────────────────────────────────────────

async def schedule_meeting_prep_jobs(app, settings) -> int:
    """Scan today's meetings and schedule prep notifications at T-5min.

    Call this from the morning briefing or on bot start.
    Returns number of jobs scheduled.
    """
    from datetime import datetime, timedelta, timezone

    graph = app.bot_data.get("graph")
    if not graph:
        return 0

    _IST = timezone(timedelta(hours=5, minutes=30))

    try:
        meetings = await get_today(graph)
    except Exception:
        logger.warning("Could not fetch today's meetings for prep scheduling")
        return 0

    now = datetime.now(_IST)
    scheduled = 0

    for m in meetings:
        if m.get("is_all_day"):
            continue

        # Parse start time (we have "10:30 AM" format)
        start_str = m.get("start", "")
        if not start_str:
            continue

        try:
            # Reconstruct today's datetime from the time string
            time_parts = datetime.strptime(start_str, "%I:%M %p")
            meeting_dt = now.replace(
                hour=time_parts.hour,
                minute=time_parts.minute,
                second=0,
                microsecond=0,
            )
            # Prep notification = 5 min before
            prep_dt = meeting_dt - timedelta(minutes=5)

            if prep_dt <= now:
                continue  # Already passed

            # Schedule the prep job
            app.job_queue.run_once(
                _prep_notification_job,
                when=prep_dt,
                data={"meeting": m, "chat_id": settings.harvey_chat_id},
                name=f"prep:{m.get('id', '')[:16]}",
            )
            scheduled += 1
            logger.info(
                "Scheduled prep for '%s' at %s",
                m.get("subject", "?")[:30],
                prep_dt.strftime("%I:%M %p"),
            )

        except (ValueError, TypeError):
            logger.debug("Could not parse meeting time: %s", start_str)
            continue

    logger.info("Scheduled %d meeting prep notifications", scheduled)
    return scheduled


async def _prep_notification_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a meeting prep notification (called by JobQueue)."""
    job_data = context.job.data
    meeting = job_data.get("meeting", {})
    chat_id = job_data.get("chat_id")

    if not chat_id:
        return

    attendees = meeting.get("attendees", [])
    talking_points = _generate_talking_points(meeting)

    card = format_meeting_card(
        subject=meeting.get("subject", "Meeting"),
        time=meeting.get("start", "?"),
        duration=meeting.get("duration", ""),
        location=meeting.get("location", ""),
        attendees=attendees,
        context="Meeting starting in 5 minutes.",
        talking_points=talking_points,
        join_url=meeting.get("join_url", ""),
    )

    kb_buttons = []
    join_url = meeting.get("join_url", "")
    if join_url:
        kb_buttons.append([InlineKeyboardButton("🔗 Join Now", url=join_url)])
    kb = InlineKeyboardMarkup(kb_buttons) if kb_buttons else None

    try:
        await context.bot.send_message(
            chat_id,
            card,
            parse_mode="MarkdownV2",
            reply_markup=kb,
        )
    except Exception:
        logger.exception("Failed to send prep notification")


# ── ConversationHandler Factory ─────────────────────────────────────────

def build_calendar_conversation() -> ConversationHandler:
    """Build the calendar ConversationHandler.

    Flow:
      /cal → CALENDAR_DAY ↔ CALENDAR_WEEK
                ↕ detail → MEETING_DETAIL ↔ MEETING_PREP
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("cal", cal_command),
            CommandHandler("calendar", cal_command),  # alias
        ],
        states={
            State.CALENDAR_DAY: [
                CallbackQueryHandler(cal_day_callback, pattern=r"^cal:"),
            ],
            State.CALENDAR_WEEK: [
                CallbackQueryHandler(cal_week_callback, pattern=r"^cal:"),
            ],
            State.MEETING_DETAIL: [
                CallbackQueryHandler(meeting_detail_callback, pattern=r"^cal:"),
            ],
            State.MEETING_PREP: [
                CallbackQueryHandler(meeting_detail_callback, pattern=r"^cal:"),
            ],
        },
        fallbacks=[],
        name="calendar_flow",
        persistent=False,
        per_message=False,
    )
