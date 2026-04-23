"""Request/response logging middleware."""

from __future__ import annotations

import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def log_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming update for debugging."""
    user = update.effective_user
    chat = update.effective_chat
    text = ""

    if update.message and update.message.text:
        text = update.message.text[:50]
    elif update.callback_query and update.callback_query.data:
        text = f"[callback] {update.callback_query.data}"

    logger.info(
        "← %s (chat=%s) %s",
        user.first_name if user else "?",
        chat.id if chat else "?",
        text,
    )

    # Store request timestamp for response time tracking
    context.user_data["_request_time"] = time.monotonic()
