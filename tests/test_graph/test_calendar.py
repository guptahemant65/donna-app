"""Tests for Graph Calendar module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from donna_bot.graph.calendar import calc_focus_time, get_today


@pytest.fixture
def mock_graph() -> MagicMock:
    g = MagicMock()
    g.get = AsyncMock()
    return g


def _make_meeting(subject: str, start_hour: int, duration_min: int = 30) -> dict:
    """Helper: create a Graph meeting event."""
    return {
        "subject": subject,
        "start": {"dateTime": f"2026-04-23T{start_hour:02d}:00:00"},
        "end": {"dateTime": f"2026-04-23T{start_hour:02d}:{duration_min:02d}:00"},
        "location": {"displayName": "Room 4B"},
        "attendees": [
            {"emailAddress": {"name": "Alice", "address": "alice@ms.com"}},
        ],
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/meet/123"},
        "isAllDay": False,
        "isCancelled": False,
    }


class TestGetToday:
    async def test_returns_parsed_meetings(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {
            "value": [
                _make_meeting("Standup", 10, 15),
                _make_meeting("1:1 Manager", 11, 30),
            ]
        }
        result = await get_today(mock_graph)
        assert len(result) == 2
        assert result[0]["subject"] == "Standup"
        assert result[1]["subject"] == "1:1 Manager"
        assert result[0]["start"] == "10:00 AM"

    async def test_skips_cancelled(self, mock_graph: MagicMock) -> None:
        cancelled = _make_meeting("Cancelled", 14)
        cancelled["isCancelled"] = True
        mock_graph.get.return_value = {
            "value": [_make_meeting("Active", 10), cancelled]
        }
        result = await get_today(mock_graph)
        assert len(result) == 1

    async def test_empty_calendar(self, mock_graph: MagicMock) -> None:
        mock_graph.get.return_value = {"value": []}
        result = await get_today(mock_graph)
        assert result == []


class TestCalcFocusTime:
    def test_full_day_free(self) -> None:
        result = calc_focus_time([])
        assert result["focus_hours"] == 8.0
        assert result["meeting_count"] == 0

    def test_half_day_meetings(self) -> None:
        meetings = [
            {"duration_minutes": 60, "start_hour": 10, "is_all_day": False},
            {"duration_minutes": 60, "start_hour": 11, "is_all_day": False},
            {"duration_minutes": 60, "start_hour": 14, "is_all_day": False},
            {"duration_minutes": 60, "start_hour": 15, "is_all_day": False},
        ]
        result = calc_focus_time(meetings)
        assert result["meeting_hours"] == 4.0
        assert result["focus_hours"] == 4.0
        assert result["meeting_count"] == 4

    def test_overloaded_day(self) -> None:
        meetings = [
            {"duration_minutes": 60, "start_hour": h, "is_all_day": False}
            for h in range(9, 18)
        ]
        result = calc_focus_time(meetings)
        assert result["focus_hours"] == 0.0

    def test_busiest_slot(self) -> None:
        meetings = [
            {"duration_minutes": 30, "start_hour": 10, "is_all_day": False},
            {"duration_minutes": 30, "start_hour": 10, "is_all_day": False},
            {"duration_minutes": 30, "start_hour": 14, "is_all_day": False},
        ]
        result = calc_focus_time(meetings)
        assert result["busiest_slot"] == "10:00"
