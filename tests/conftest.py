"""Shared test fixtures for Donna Bot tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_token() -> str:
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.test.signature"


@pytest.fixture
def mock_graph_response() -> dict:
    """Standard Graph API response envelope."""
    return {"value": [], "@odata.count": 0}


@pytest.fixture
def mock_update() -> MagicMock:
    """Mock Telegram Update object."""
    update = MagicMock()
    update.effective_chat.id = 496116833
    update.effective_user.first_name = "Harvey"
    update.effective_user.id = 496116833
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_markdown_v2 = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Mock Telegram CallbackContext."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.send_chat_action = AsyncMock()
    context.user_data = {}
    context.job_queue = MagicMock()
    return context
