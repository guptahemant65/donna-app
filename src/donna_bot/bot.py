"""Donna Bot — Application factory and handler registration."""

from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from donna_bot.auth.token_manager import TokenManager
from donna_bot.config import Settings
from donna_bot.graph.client import GraphClient
from donna_bot.handlers.briefing import brief_handler
from donna_bot.handlers.start import help_handler, start_handler
from donna_bot.middleware.logging_mw import log_request
from donna_bot.scheduler.jobs import schedule_eod_summary, schedule_morning_briefing

logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
# Quiet noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


def create_app(settings: Settings | None = None) -> Application:
    """Build and configure the Donna Telegram bot."""
    if settings is None:
        settings = Settings.from_env()

    # Auth + Graph
    token_mgr = TokenManager(
        app_id=settings.graph_app_id,
        tenant_id=settings.graph_tenant_id,
    )
    graph = GraphClient(token_manager=token_mgr)

    app = (
        Application.builder()
        .token(settings.telegram_token)
        .build()
    )

    # Store shared resources in bot_data
    app.bot_data["settings"] = settings
    app.bot_data["token_mgr"] = token_mgr
    app.bot_data["graph"] = graph

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("brief", brief_handler))

    # Scheduled jobs
    schedule_morning_briefing(app, settings)
    schedule_eod_summary(app, settings)

    logger.info(
        "Donna is ready — listening for Harvey (chat_id=%s)",
        settings.harvey_chat_id,
    )

    return app


def _with_logging(handler):
    """Wrap a handler to log requests first."""

    async def wrapper(update, context):
        await log_request(update, context)
        return await handler(update, context)

    return wrapper
