"""Tests for configuration loading."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from donna_bot.config import Settings


class TestSettings:
    def test_loads_from_env(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "test-token-123",
            "HARVEY_CHAT_ID": "99887766",
            "GRAPH_APP_ID": "d3590ed6-test",
            "GRAPH_TENANT_ID": "72f988bf-test",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.telegram_token == "test-token-123"
            assert s.harvey_chat_id == 99887766
            assert s.graph_app_id == "d3590ed6-test"

    def test_missing_token_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
                Settings.from_env()

    def test_feature_flags_default_on(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "t",
            "HARVEY_CHAT_ID": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.feature_briefing is True
            assert s.feature_email is True
            assert s.feature_pr is False

    def test_schedule_defaults(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "t",
            "HARVEY_CHAT_ID": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.briefing_hour == 8
            assert s.briefing_minute == 30
