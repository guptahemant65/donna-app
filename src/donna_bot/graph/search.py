"""Graph Search — cross-tenant M365 search via /search/query.

Searches across:
  - messages (emails + Teams chats)
  - driveItem (OneDrive/SharePoint files)
  - event (calendar events)
  - listItem (SharePoint list items)

Uses POST /search/query with KQL syntax.
"""

from __future__ import annotations

import logging
from typing import Any

from donna_bot.graph.client import GraphClient

logger = logging.getLogger(__name__)

# Entity types we search across
ENTITY_TYPES = ["message", "driveItem", "event"]


async def search_m365(
    graph: GraphClient,
    query: str,
    entity_types: list[str] | None = None,
    top: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """Search across M365 using the search/query API.

    Returns dict keyed by entity type, each containing a list of hits.
    """
    if entity_types is None:
        entity_types = ENTITY_TYPES

    # Build search request payload
    requests_payload = []
    for et in entity_types:
        requests_payload.append({
            "entityTypes": [et],
            "query": {"queryString": query},
            "from": 0,
            "size": top,
        })

    data = await graph.post(
        "/search/query",
        json={"requests": requests_payload},
    )

    # Parse results grouped by entity type
    results: dict[str, list[dict[str, Any]]] = {}
    for response in data.get("value", []):
        for hit_container in response.get("hitsContainers", []):
            if not hit_container.get("hits"):
                continue

            for hit in hit_container["hits"]:
                resource = hit.get("resource", {})
                entity_type = resource.get("@odata.type", "unknown")
                parsed = _parse_hit(hit, entity_type)

                # Normalize entity type key
                type_key = _type_key(entity_type)
                if type_key not in results:
                    results[type_key] = []
                results[type_key].append(parsed)

    return results


def _type_key(odata_type: str) -> str:
    """Convert @odata.type to a readable key."""
    mapping = {
        "#microsoft.graph.message": "emails",
        "#microsoft.graph.driveItem": "files",
        "#microsoft.graph.event": "events",
        "#microsoft.graph.listItem": "lists",
        "#microsoft.graph.chatMessage": "chats",
    }
    return mapping.get(odata_type, "other")


def _parse_hit(hit: dict[str, Any], entity_type: str) -> dict[str, Any]:
    """Parse a single search hit into a clean dict."""
    resource = hit.get("resource", {})
    summary = hit.get("summary", "")

    base = {
        "id": resource.get("id", ""),
        "summary": summary,
        "rank": hit.get("rank", 0),
    }

    odata = resource.get("@odata.type", "")

    if "#microsoft.graph.message" in odata:
        base.update({
            "type": "email",
            "subject": resource.get("subject", "(No subject)"),
            "from": _extract_sender(resource),
            "date": resource.get("receivedDateTime", ""),
            "preview": resource.get("bodyPreview", "")[:100],
            "webLink": resource.get("webLink", ""),
        })
    elif "#microsoft.graph.driveItem" in odata:
        base.update({
            "type": "file",
            "name": resource.get("name", "?"),
            "webUrl": resource.get("webUrl", ""),
            "lastModified": resource.get("lastModifiedDateTime", ""),
            "size": resource.get("size", 0),
            "createdBy": resource.get("createdBy", {}).get("user", {}).get("displayName", ""),
        })
    elif "#microsoft.graph.event" in odata:
        base.update({
            "type": "event",
            "subject": resource.get("subject", "(No subject)"),
            "start": resource.get("start", {}).get("dateTime", ""),
            "end": resource.get("end", {}).get("dateTime", ""),
            "organizer": resource.get("organizer", {}).get("emailAddress", {}).get("name", ""),
        })
    else:
        base.update({
            "type": "other",
            "name": resource.get("name", resource.get("subject", "?")),
        })

    return base


def _extract_sender(resource: dict[str, Any]) -> str:
    """Extract sender display name from a message resource."""
    sender = resource.get("sender", {}) or resource.get("from", {})
    email_address = sender.get("emailAddress", {})
    return email_address.get("name", email_address.get("address", "?"))
