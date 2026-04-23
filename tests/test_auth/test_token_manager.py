"""Tests for token management."""

from __future__ import annotations

from donna_bot.auth.token_manager import TokenManager


class TestTokenManager:
    def test_no_token_initially(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        assert tm.has_valid_token is False

    def test_set_token_marks_valid(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=3600)
        assert tm.has_valid_token is True
        assert tm.access_token == "abc123"

    def test_expired_token_invalid(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=-10)
        assert tm.has_valid_token is False

    def test_token_near_expiry_triggers_refresh(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=60)
        assert tm.needs_refresh is True

    def test_token_with_long_expiry_no_refresh(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=3600)
        assert tm.needs_refresh is False

    def test_headers_returns_bearer(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("mytoken", expires_in=3600)
        h = tm.auth_headers
        assert h["Authorization"] == "Bearer mytoken"

    def test_invalidate_clears_token(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=3600)
        tm.invalidate()
        assert tm.has_valid_token is False
        assert tm.access_token is None
