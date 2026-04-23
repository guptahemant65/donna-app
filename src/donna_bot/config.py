"""Configuration — loads from .env file and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise ValueError(
            f"Missing required env var: {key}. Copy .env.example to .env and fill in values."
        )
    return val


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(int(default))) == "1"


def _env_int(key: str, default: int = 0) -> int:
    return int(os.environ.get(key, str(default)))


@dataclass(frozen=True)
class Settings:
    """All Donna configuration — single source of truth."""

    # Telegram
    telegram_token: str
    harvey_chat_id: int

    # Graph Auth
    graph_app_id: str = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
    graph_tenant_id: str = "72f988bf-86f1-41af-91ab-2d7cd011db47"
    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    # Feature Flags
    feature_briefing: bool = True
    feature_email: bool = True
    feature_calendar: bool = True
    feature_people: bool = True
    feature_search: bool = True
    feature_pr: bool = False
    feature_food: bool = False
    feature_focus: bool = False

    # Azure DevOps (for PR Intelligence)
    ado_pat: str = ""
    ado_email: str = ""
    ado_repos_json: str = ""

    # Schedule (24h, IST)
    briefing_hour: int = 8
    briefing_minute: int = 30
    eod_hour: int = 18
    eod_minute: int = 30

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            telegram_token=_env("TELEGRAM_BOT_TOKEN"),
            harvey_chat_id=int(_env("HARVEY_CHAT_ID", "0")),
            graph_app_id=_env("GRAPH_APP_ID", "14d82eec-204b-4c2f-b7e8-296a70dab67e"),
            graph_tenant_id=_env("GRAPH_TENANT_ID", "72f988bf-86f1-41af-91ab-2d7cd011db47"),
            feature_briefing=_env_bool("FEATURE_BRIEFING", True),
            feature_email=_env_bool("FEATURE_EMAIL", True),
            feature_calendar=_env_bool("FEATURE_CALENDAR", True),
            feature_people=_env_bool("FEATURE_PEOPLE", True),
            feature_search=_env_bool("FEATURE_SEARCH", True),
            feature_pr=_env_bool("FEATURE_PR", False),
            feature_food=_env_bool("FEATURE_FOOD", False),
            feature_focus=_env_bool("FEATURE_FOCUS", False),
            ado_pat=os.environ.get("ADO_PAT", ""),
            ado_email=os.environ.get("ADO_EMAIL", ""),
            ado_repos_json=os.environ.get("ADO_REPOS", ""),
            briefing_hour=_env_int("BRIEFING_HOUR", 8),
            briefing_minute=_env_int("BRIEFING_MINUTE", 30),
            eod_hour=_env_int("EOD_HOUR", 18),
            eod_minute=_env_int("EOD_MINUTE", 30),
        )
