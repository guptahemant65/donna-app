"""Start and help handlers — first impressions matter."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from donna_bot.formatters.escape import md2, md2_bold, md2_header, md2_separator
from donna_bot.middleware.security import harvey_only

logger = logging.getLogger(__name__)


@harvey_only
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — Donna introduces herself."""
    name = update.effective_user.first_name if update.effective_user else "boss"

    lines = [
        md2_header(),
        "",
        f"Morning, {md2_bold(name)}\\. I'm awake\\.",
        "",
        md2("Your AI concierge is online."),
        md2("I know your calendar, your inbox, your team,"),
        md2("and when you need coffee."),
        "",
        f"Type {md2('/brief')} for your morning briefing,",
        f"or {md2('/help')} to see what I can do\\.",
        "",
        md2_separator(),
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
    )


@harvey_only
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show available commands."""
    lines = [
        md2_header(),
        "",
        md2_bold("What I can do:"),
        "",
        f"📬 {md2('/brief')}  — Morning briefing",
        f"📧 {md2('/mail')}   — Email inbox",
        f"📅 {md2('/cal')}    — Today's calendar",
        f"👥 {md2('/who')}    — People lookup",
        f"🔍 {md2('/search')} — Search everything",
        "",
        md2_bold("Coming soon:"),
        f"🔧 {md2('/pr')}     — PR intelligence",
        f"☕ {md2('/coffee')}  — Order coffee",
        f"🎯 {md2('/focus')}  — Focus mode",
        f"📝 {md2('/tasks')}  — Tasks & reminders",
        "",
        md2_italic("Or just talk to me — I understand natural language too\\."),
        "",
        md2_separator(),
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="MarkdownV2",
    )
