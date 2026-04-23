"""Donna's state machine — every possible conversation state."""

from __future__ import annotations

from enum import IntEnum, auto


class State(IntEnum):
    """All states Donna can be in during a conversation."""

    IDLE = auto()
    ONBOARDING = auto()

    # Briefing
    BRIEFING = auto()

    # Email flow
    EMAIL_LIST = auto()
    EMAIL_READ = auto()
    EMAIL_COMPOSE = auto()

    # Calendar flow
    CALENDAR_DAY = auto()
    CALENDAR_WEEK = auto()
    MEETING_DETAIL = auto()
    MEETING_PREP = auto()

    # People flow
    PEOPLE_SEARCH = auto()
    PEOPLE_DETAIL = auto()
    ORG_CHART = auto()

    # Search
    SEARCH_QUERY = auto()
    SEARCH_RESULTS = auto()

    # Engineering
    PR_LIST = auto()
    PR_DETAIL = auto()
    INCIDENT = auto()
    INCIDENT_ANALYSIS = auto()

    # Life
    FOCUS = auto()
    FOOD_ORDER = auto()
    FOOD_TRACKING = auto()
    TASKS = auto()
    REMINDER = auto()

    # Meta
    SETTINGS = auto()
    HELP = auto()
    ERROR = auto()
