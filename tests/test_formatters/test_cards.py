"""Tests for card template rendering."""

from __future__ import annotations

from donna_bot.formatters.cards import (
    format_briefing_card,
    format_email_card,
    format_meeting_card,
    format_person_card,
)


class TestBriefingCard:
    def test_renders_with_all_sections(self) -> None:
        result = format_briefing_card(
            incidents=[{"severity": "Sev2", "title": "LiveTable refresh", "status": "mitigated"}],
            emails=[
                {"from": "Priya", "subject": "Design spec sign-off"},
                {"from": "Manager", "subject": "Migration timeline"},
            ],
            meetings=[
                {"subject": "Standup", "start": "10:30", "duration": "15m"},
                {"subject": "1:1 Manager", "start": "11:00", "duration": "30m"},
            ],
            sprint={"done": 18, "total": 23},
            weather={"temp": 27, "condition": "Clear", "commute": "35min"},
        )
        assert "MORNING BRIEFING" in result
        assert "Priya" in result
        assert "Standup" in result
        assert "18" in result

    def test_renders_without_incidents(self) -> None:
        result = format_briefing_card(
            incidents=[],
            emails=[],
            meetings=[],
            sprint={"done": 0, "total": 0},
        )
        assert "All clear" in result


class TestEmailCard:
    def test_renders_email(self) -> None:
        result = format_email_card(
            sender="Priya Sharma",
            to="Harvey",
            date="Apr 23, 10:15 AM",
            subject="Design spec — need your sign-off",
            body="The notification system design spec is ready for review.",
            has_attachments=False,
        )
        assert "Priya Sharma" in result
        assert "Design spec" in result


class TestMeetingCard:
    def test_renders_meeting_with_prep(self) -> None:
        result = format_meeting_card(
            subject="1:1 with Manager",
            time="11:00 AM",
            duration="30 min",
            location="Room 4B",
            attendees=["Harvey", "Sarah Kim"],
            context="Last 1:1 was 2 weeks ago",
            talking_points=["Sprint on track", "Flaky test costing CI time"],
            join_url="https://teams.microsoft.com/meet/123",
        )
        assert "1:1 with Manager" in result
        assert "11:00 AM" in result
        assert "Sprint on track" in result


class TestPersonCard:
    def test_renders_person(self) -> None:
        result = format_person_card(
            name="Alice Chen",
            title="Senior Software Engineer",
            department="Platform Team",
            location="Bangalore",
            availability="Available",
            email="alicec@microsoft.com",
            manager="Sarah Kim",
        )
        assert "Alice Chen" in result
        assert "Senior Software Engineer" in result
        assert "Available" in result
