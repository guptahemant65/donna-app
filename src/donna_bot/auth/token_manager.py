"""Token manager — caches Graph tokens with auto-refresh."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_REFRESH_BUFFER_SECS = 300  # Refresh 5 minutes before expiry


class TokenManager:
    """Manages Graph API access tokens with caching and refresh."""

    def __init__(self, app_id: str, tenant_id: str) -> None:
        self.app_id = app_id
        self.tenant_id = tenant_id
        self._token: str | None = None
        self._expires_at: float = 0.0

    def set_token(self, token: str, expires_in: int) -> None:
        self._token = token
        self._expires_at = time.monotonic() + expires_in

    @property
    def has_valid_token(self) -> bool:
        return self._token is not None and time.monotonic() < self._expires_at

    @property
    def needs_refresh(self) -> bool:
        if self._token is None:
            return True
        return time.monotonic() > (self._expires_at - _REFRESH_BUFFER_SECS)

    @property
    def access_token(self) -> str | None:
        if self.has_valid_token:
            return self._token
        return None

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def ensure_token(self) -> str:
        """Get a valid token, refreshing via WAM if needed.

        Raises RuntimeError if no token can be acquired.
        """
        if self.has_valid_token and not self.needs_refresh:
            return self._token  # type: ignore[return-value]

        from donna_bot.auth.wam import acquire_token_wam

        token, expires_in = acquire_token_wam(self.app_id, self.tenant_id)
        if token:
            self.set_token(token, expires_in)
            return token

        if self.has_valid_token:
            logger.warning("WAM refresh failed — using existing token (expires soon)")
            return self._token  # type: ignore[return-value]

        raise RuntimeError(
            "Cannot acquire Graph token. Is Harvey's Windows session active?"
        )

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0
