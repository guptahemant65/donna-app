"""WAM Broker authentication — Windows SSO for Graph tokens.

Extracted from poc/graph_probe.py. This ONLY works on Windows with
an active Microsoft corp SSO session. For cloud deployment, swap
this module for client_credentials.py (future ADR-003).
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_HAS_WAM = False
try:
    import pymsalruntime

    _HAS_WAM = True
except ImportError:
    logger.warning("pymsalruntime not available — WAM auth disabled")


def acquire_token_wam(
    app_id: str,
    tenant_id: str,
    timeout: float = 15.0,
) -> tuple[str | None, int]:
    """Acquire Graph token via WAM broker (silent, no UI).

    Returns (access_token, expires_in_seconds) or (None, 0).
    """
    if not _HAS_WAM:
        return None, 0

    event = threading.Event()
    disc_result: list = [None]

    def disc_cb(r: object) -> None:
        disc_result[0] = r
        event.set()

    pymsalruntime.discover_accounts(
        app_id,
        "00000000-0000-0000-0000-000000000001",
        disc_cb,
    )
    event.wait(timeout)

    if not disc_result[0]:
        logger.error("No Windows SSO accounts found")
        return None, 0

    ms_account = None
    for a in disc_result[0].get_accounts():
        if "microsoft.com" in a.get_user_name():
            ms_account = a
            break

    if not ms_account:
        logger.error("No Microsoft corp account in Windows SSO")
        return None, 0

    logger.info("Found SSO account: %s", ms_account.get_user_name())

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ["https://graph.microsoft.com/.default"]

    event2 = threading.Event()
    tok_result: list = [None]

    def tok_cb(r: object) -> None:
        tok_result[0] = r
        event2.set()

    params = pymsalruntime.MSALRuntimeAuthParameters(app_id, authority)
    params.set_requested_scopes(scopes)

    pymsalruntime.acquire_token_silently(
        params,
        "00000000-0000-0000-0000-000000000002",
        ms_account,
        tok_cb,
    )
    event2.wait(timeout)

    r = tok_result[0]
    if r:
        token = r.get_access_token()
        if token and len(token) > 50:
            logger.info("Token acquired via WAM broker")
            return token, 3600
        else:
            error = (r.get_error() or "empty token")[:200]
            logger.error("WAM token error: %s", error)

    return None, 0
