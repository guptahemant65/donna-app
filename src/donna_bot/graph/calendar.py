"""Graph Calendar — meetings, focus time, free/busy."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from donna_bot.graph.client import GraphClient

logger = logging.getLogger(__name__)

# IST offset
_IST = timezone(timedelta(hours=5, minutes=30))


def _now_ist() -> datetime:
    return datetime.now(_IST)


def _format_dt(dt: datetime) -> str:
    """ISO format without timezone for Graph calendarView."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


async def get_today(graph: GraphClient) -> list[dict[str, Any]]:
    """Fetch today's meetings from calendarView."""
    now = _now_ist()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    data = await graph.get(
        "/me/calendarView",
        params={
            "startDateTime": _format_dt(start),
            "endDateTime": _format_dt(end),
            "$select": "subject,start,end,location,attendees,onlineMeeting,isAllDay,isCancelled",
            "$orderby": "start/dateTime",
            "$top": "50",
        },
    )
    meetings = data.get("value", [])
    return [_parse_meeting(m) for m in meetings if not m.get("isCancelled", False)]


async def get_week(graph: GraphClient) -> list[dict[str, Any]]:
    """Fetch this week's meetings (Mon-Fri)."""
    now = _now_ist()
    # Start from today, go 7 days
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    data = await graph.get(
        "/me/calendarView",
        params={
            "startDateTime": _format_dt(start),
            "endDateTime": _format_dt(end),
            "$select": "subject,start,end,location,attendees,onlineMeeting,isAllDay,isCancelled",
            "$orderby": "start/dateTime",
            "$top": "100",
        },
    )
    meetings = data.get("value", [])
    return [_parse_meeting(m) for m in meetings if not m.get("isCancelled", False)]


def calc_focus_time(meetings: list[dict[str, Any]], work_hours: int = 8) -> dict[str, Any]:
    """Calculate available focus time based on meeting gaps.

    Returns: total_meeting_hours, focus_hours, meeting_count, busiest_slot.
    """
    if not meetings:
        return {
            "meeting_hours": 0.0,
            "focus_hours": float(work_hours),
            "meeting_count": 0,
            "busiest_slot": None,
        }

    total_minutes = 0
    for m in meetings:
        if m.get("is_all_day"):
            continue
        duration = m.get("duration_minutes", 30)
        total_minutes += duration

    meeting_hours = total_minutes / 60.0
    focus_hours = max(0.0, work_hours - meeting_hours)

    # Find busiest hour slot
    hour_counts: dict[int, int] = {}
    for m in meetings:
        start_hour = m.get("start_hour", 9)
        hour_counts[start_hour] = hour_counts.get(start_hour, 0) + 1

    busiest = max(hour_counts, key=hour_counts.get) if hour_counts else None

    return {
        "meeting_hours": round(meeting_hours, 1),
        "focus_hours": round(focus_hours, 1),
        "meeting_count": len(meetings),
        "busiest_slot": f"{busiest}:00" if busiest is not None else None,
    }


def _parse_meeting(m: dict[str, Any]) -> dict[str, Any]:
    """Parse a Graph meeting event into a clean dict."""
    start_raw = m.get("start", {}).get("dateTime", "")
    end_raw = m.get("end", {}).get("dateTime", "")

    # Parse ISO datetime
    start_dt = _safe_parse_dt(start_raw)
    end_dt = _safe_parse_dt(end_raw)

    duration_minutes = 30
    if start_dt and end_dt:
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

    start_hour = start_dt.hour if start_dt else 9
    start_time = start_dt.strftime("%I:%M %p").lstrip("0") if start_dt else ""

    # Location
    location = ""
    loc_data = m.get("location", {})
    if isinstance(loc_data, dict):
        location = loc_data.get("displayName", "")

    # Join URL
    join_url = None
    online = m.get("onlineMeeting")
    if isinstance(online, dict):
        join_url = online.get("joinUrl", "")

    # Attendees
    attendees = []
    for a in m.get("attendees", []):
        email_addr = a.get("emailAddress", {})
        attendees.append(email_addr.get("name", email_addr.get("address", "?")))

    return {
        "id": m.get("id", ""),
        "subject": m.get("subject", "(No subject)"),
        "start": start_time,
        "start_hour": start_hour,
        "duration": f"{duration_minutes}m",
        "duration_minutes": duration_minutes,
        "location": location,
        "join_url": join_url,
        "attendees": attendees,
        "is_all_day": m.get("isAllDay", False),
    }


def _safe_parse_dt(raw: str) -> datetime | None:
    """Parse Graph datetime string (may have fractional seconds)."""
    if not raw:
        return None
    try:
        # Remove trailing Z and fractional seconds for parsing
        clean = raw.rstrip("Z").split(".")[0]
        return datetime.fromisoformat(clean)
    except (ValueError, TypeError):
        return None
