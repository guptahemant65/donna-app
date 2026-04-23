"""Live-updating progress messages — the typing dance."""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from donna_bot.formatters.escape import md2, md2_bold, md2_header

logger = logging.getLogger(__name__)


async def send_progress(
    bot: Bot,
    chat_id: int,
    steps: list[tuple[int, str]],
    width: int = 15,
) -> int:
    """Send a live-updating progress message.

    Args:
        bot: Telegram Bot instance
        chat_id: Chat to send to
        steps: List of (percentage, status_text) tuples
        width: Progress bar width in chars

    Returns:
        message_id of the progress message (for later replacement)
    """
    if not steps:
        return 0

    pct, status = steps[0]
    text = _render_progress(pct, status, width)
    msg = await bot.send_message(chat_id, text, parse_mode="MarkdownV2")

    for pct, status in steps[1:]:
        await asyncio.sleep(0.8)
        text = _render_progress(pct, status, width)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=msg.message_id, parse_mode="MarkdownV2"
            )
        except Exception:
            logger.debug("Progress edit failed (message unchanged)")

    return msg.message_id


def progress_message(step: str, percent: int, width: int = 15) -> str:
    """Generate a progress bar message for live-editing.

    Usage: Send once, then edit_message_text with updated step/percent.
    """
    return _render_progress(percent, step, width)


def _render_progress(pct: int, status: str, width: int) -> str:
    """Render a progress bar message."""
    filled = int(width * pct / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    lines = [
        md2_header(),
        f"⏳ {md2_bold('Working on it')}\\.\\.\\.",
        "",
        md2(f"{bar}  {pct}%"),
        md2(status),
    ]
    return "\n".join(lines)
