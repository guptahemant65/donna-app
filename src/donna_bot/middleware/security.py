"""Security middleware — Harvey-only access control."""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from telegram import Update
from telegram.ext import ContextTypes

from donna_bot.config import Settings

logger = logging.getLogger(__name__)


def harvey_only(func: Callable) -> Callable:
    """Decorator: only allow Harvey's chat_id through.

    Everyone else gets silence (no response = no information leak).
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        settings: Settings = context.bot_data.get("settings")  # type: ignore[assignment]
        if not settings:
            logger.error("Settings not in bot_data — rejecting request")
            return None

        chat_id = update.effective_chat.id if update.effective_chat else 0
        if chat_id != settings.harvey_chat_id:
            logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
            return None

        return await func(update, context, *args, **kwargs)

    return wrapper
