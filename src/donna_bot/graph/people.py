"""Graph People — search, profile, org chart, presence.

Uses:
  /me/people — ranked people around Harvey
  /users?$search="displayName:<name>" — directory search (needs ConsistencyLevel)
  /users/{id}/directReports — org chart down
  /users/{id}/manager — org chart up
  /users/{id}/presence — availability status
"""

from __future__ import annotations

import logging
from typing import Any

from donna_bot.graph.client import GraphClient

logger = logging.getLogger(__name__)


async def search_people(graph: GraphClient, query: str, top: int = 10) -> list[dict[str, Any]]:
    """Search for people via /me/people (relevance-ranked).

    This returns people Harvey interacts with most, ranked by relevance.
    Includes coworkers, direct reports, collaborators.
    """
    data = await graph.get(
        "/me/people",
        params={
            "$search": f'"{query}"',
            "$select": "displayName,emailAddresses,jobTitle,department,officeLocation,userPrincipalName",
            "$top": str(top),
        },
    )
    people = data.get("value", [])
    return [_parse_person(p) for p in people]


async def get_user_profile(graph: GraphClient, user_id: str) -> dict[str, Any]:
    """Get a specific user's profile by ID or UPN."""
    data = await graph.get(
        f"/users/{user_id}",
        params={
            "$select": "id,displayName,mail,jobTitle,department,officeLocation,userPrincipalName,mobilePhone,companyName",
        },
    )
    return _parse_user(data)


async def get_user_presence(graph: GraphClient, user_id: str) -> dict[str, Any]:
    """Get a user's presence/availability."""
    try:
        data = await graph.get(f"/users/{user_id}/presence")
        return {
            "availability": data.get("availability", "PresenceUnknown"),
            "activity": data.get("activity", "PresenceUnknown"),
        }
    except Exception:
        logger.debug("Could not get presence for %s", user_id[:8])
        return {"availability": "PresenceUnknown", "activity": "PresenceUnknown"}


async def get_manager(graph: GraphClient, user_id: str) -> dict[str, Any] | None:
    """Get a user's manager."""
    try:
        data = await graph.get(
            f"/users/{user_id}/manager",
            params={
                "$select": "id,displayName,mail,jobTitle,department,userPrincipalName",
            },
        )
        return _parse_user(data)
    except Exception:
        logger.debug("No manager found for %s", user_id[:8])
        return None


async def get_direct_reports(graph: GraphClient, user_id: str, top: int = 20) -> list[dict[str, Any]]:
    """Get a user's direct reports."""
    try:
        data = await graph.get(
            f"/users/{user_id}/directReports",
            params={
                "$select": "id,displayName,mail,jobTitle,department,userPrincipalName",
                "$top": str(top),
            },
        )
        reports = data.get("value", [])
        return [_parse_user(r) for r in reports]
    except Exception:
        logger.debug("Could not get reports for %s", user_id[:8])
        return []


async def get_org_chain(graph: GraphClient, user_id: str, depth: int = 3) -> list[dict[str, Any]]:
    """Walk up the org chart from user to top, up to `depth` levels."""
    chain: list[dict[str, Any]] = []
    current_id = user_id

    for _ in range(depth):
        manager = await get_manager(graph, current_id)
        if not manager:
            break
        chain.append(manager)
        current_id = manager.get("id", "")
        if not current_id:
            break

    return chain


def _parse_person(p: dict[str, Any]) -> dict[str, Any]:
    """Parse a /me/people result into a clean dict."""
    emails = p.get("emailAddresses", [])
    primary_email = ""
    if emails:
        primary_email = emails[0].get("address", "")

    return {
        "id": p.get("id", ""),
        "name": p.get("displayName", "?"),
        "email": primary_email,
        "title": p.get("jobTitle", ""),
        "department": p.get("department", ""),
        "location": p.get("officeLocation", ""),
        "upn": p.get("userPrincipalName", ""),
    }


def _parse_user(u: dict[str, Any]) -> dict[str, Any]:
    """Parse a /users/{id} result into a clean dict."""
    return {
        "id": u.get("id", ""),
        "name": u.get("displayName", "?"),
        "email": u.get("mail", ""),
        "title": u.get("jobTitle", ""),
        "department": u.get("department", ""),
        "location": u.get("officeLocation", ""),
        "upn": u.get("userPrincipalName", ""),
        "phone": u.get("mobilePhone", ""),
        "company": u.get("companyName", ""),
    }
