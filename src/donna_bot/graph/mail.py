"""Graph Mail — inbox, read, reply, archive."""

from __future__ import annotations

import logging
from typing import Any

from donna_bot.graph.client import GraphClient

logger = logging.getLogger(__name__)


async def get_unread(graph: GraphClient, top: int = 10) -> list[dict[str, Any]]:
    """Fetch top unread emails from inbox."""
    data = await graph.get(
        "/me/messages",
        params={
            "$filter": "isRead eq false",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,importance",
            "$orderby": "receivedDateTime desc",
            "$top": str(top),
        },
    )
    messages = data.get("value", [])
    return [_parse_email_summary(m) for m in messages]


async def get_inbox(graph: GraphClient, top: int = 10, skip: int = 0) -> dict[str, Any]:
    """Fetch inbox emails (read + unread) with count."""
    data = await graph.get(
        "/me/mailFolders/Inbox/messages",
        params={
            "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments,importance",
            "$orderby": "receivedDateTime desc",
            "$top": str(top),
            "$skip": str(skip),
            "$count": "true",
        },
    )
    messages = data.get("value", [])
    total = data.get("@odata.count", len(messages))
    return {
        "emails": [_parse_email_summary(m) for m in messages],
        "total": total,
    }


async def get_email(graph: GraphClient, email_id: str) -> dict[str, Any]:
    """Fetch a single email with full body."""
    data = await graph.get(
        f"/me/messages/{email_id}",
        params={
            "$select": "id,subject,from,toRecipients,receivedDateTime,body,hasAttachments,importance,conversationId",
        },
    )
    return _parse_email_full(data)


async def reply(graph: GraphClient, email_id: str, body: str) -> None:
    """Reply to an email."""
    await graph.post(
        f"/me/messages/{email_id}/reply",
        json={
            "message": {
                "body": {
                    "contentType": "Text",
                    "content": body,
                },
            },
        },
    )
    logger.info("Replied to email %s", email_id[:8])


async def archive(graph: GraphClient, email_id: str) -> None:
    """Archive an email by moving to Archive folder."""
    # First get the Archive folder ID
    folders = await graph.get(
        "/me/mailFolders",
        params={"$filter": "displayName eq 'Archive'"},
    )
    archive_folders = folders.get("value", [])

    if archive_folders:
        folder_id = archive_folders[0]["id"]
        await graph.post(
            f"/me/messages/{email_id}/move",
            json={"destinationId": folder_id},
        )
        logger.info("Archived email %s", email_id[:8])
    else:
        # Fallback: mark as read
        logger.warning("No Archive folder found — marking as read instead")
        await graph.patch(
            f"/me/messages/{email_id}",
            json={"isRead": True},
        )


async def mark_read(graph: GraphClient, email_id: str) -> None:
    """Mark an email as read."""
    await graph.patch(
        f"/me/messages/{email_id}",
        json={"isRead": True},
    )


def _parse_email_summary(m: dict[str, Any]) -> dict[str, Any]:
    """Parse a Graph message into a compact summary."""
    from_data = m.get("from", {}).get("emailAddress", {})
    return {
        "id": m.get("id", ""),
        "subject": m.get("subject", "(no subject)"),
        "from": from_data.get("name", from_data.get("address", "?")),
        "from_email": from_data.get("address", ""),
        "date": _format_date(m.get("receivedDateTime", "")),
        "preview": m.get("bodyPreview", "")[:100],
        "isRead": m.get("isRead", True),
        "hasAttachments": m.get("hasAttachments", False),
        "importance": m.get("importance", "normal"),
    }


def _parse_email_full(m: dict[str, Any]) -> dict[str, Any]:
    """Parse a full email with body."""
    summary = _parse_email_summary(m)

    body_data = m.get("body", {})
    body_content = body_data.get("content", "")
    body_type = body_data.get("contentType", "text")

    # Strip HTML if needed (basic — just remove tags)
    if body_type.lower() == "html":
        import re
        body_content = re.sub(r"<[^>]+>", "", body_content)
        body_content = re.sub(r"\s+", " ", body_content).strip()

    to_list = []
    for r in m.get("toRecipients", []):
        addr = r.get("emailAddress", {})
        to_list.append(addr.get("name", addr.get("address", "?")))

    summary.update({
        "body": body_content[:2000],  # Telegram message limit
        "to": to_list,
        "conversationId": m.get("conversationId", ""),
    })
    return summary


def _format_date(iso_str: str) -> str:
    """Format ISO datetime to readable string."""
    if not iso_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.rstrip("Z"))
        return dt.strftime("%b %d, %I:%M %p").lstrip("0")
    except (ValueError, TypeError):
        return iso_str[:16]
