"""Graph /me — profile and presence."""

from __future__ import annotations

import logging
from typing import Any

from donna_bot.graph.client import GraphClient

logger = logging.getLogger(__name__)


async def get_profile(graph: GraphClient) -> dict[str, Any]:
    """Fetch Harvey's profile from /me.

    Returns: displayName, mail, jobTitle, officeLocation, department.
    """
    data = await graph.get(
        "/me",
        params={"$select": "displayName,mail,jobTitle,officeLocation,department,userPrincipalName"},
    )
    return {
        "displayName": data.get("displayName", ""),
        "mail": data.get("mail", ""),
        "jobTitle": data.get("jobTitle", ""),
        "officeLocation": data.get("officeLocation", ""),
        "department": data.get("department", ""),
        "upn": data.get("userPrincipalName", ""),
    }


async def get_presence(graph: GraphClient) -> dict[str, Any]:
    """Fetch current presence status from /me/presence.

    Returns: availability (Available, Busy, Away, DoNotDisturb, Offline),
             activity (InACall, InAMeeting, Presenting, etc.).
    """
    data = await graph.get("/me/presence")
    return {
        "availability": data.get("availability", "Offline"),
        "activity": data.get("activity", "Offline"),
    }
