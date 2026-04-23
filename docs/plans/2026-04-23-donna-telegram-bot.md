# Donna Telegram Bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the most advanced, creative, beautiful Telegram bot that IS Donna — Harvey's always-available AI concierge with full Microsoft Graph integration, proactive intelligence, and a personality that feels alive.

**Architecture:** Single-user async Telegram bot (python-telegram-bot v21) running locally on Harvey's machine, authenticating to Microsoft Graph via WAM broker. ConversationHandler state machine manages multi-step flows. JobQueue powers proactive scheduling (morning briefings, meeting prep, EOD summaries). Every response uses a rich visual design system with MarkdownV2, Unicode art, inline keyboards, and live-updating progress messages.

**Tech Stack:** Python 3.12+, python-telegram-bot 21.x (async), httpx (async HTTP), pymsalruntime (WAM auth), aiosqlite (local state), pytest + pytest-asyncio (testing)

---

## I. The Vision — What Makes This Bot Extraordinary

This isn't a command-response chatbot. This is Donna — she has a personality, she anticipates needs, she knows everything about Harvey's work life, and she communicates with style.

**The Donna Moments:**
1. **The Wake-Up** — Bot starts and sends: "Morning, Harvey. I'm awake. Your day looks... interesting. Want the briefing?"
2. **The Typing Dance** — For complex queries, a progress message appears and EDITS itself as data loads: "Reading 47 emails..." → "Found 3 that matter..." → [Full briefing]
3. **The Anticipation** — 8:30 AM briefing arrives unprompted. 5 min before meetings, a prep card appears. End of day, a wrap-up.
4. **The Personality** — "12 hours online, Harvey. The build is green. Go home." / "Your 1:1 is in 5 min. Alice is carrying 60% of reviews — worth mentioning."
5. **The Live Dashboard** — Pin the morning briefing to the top of chat. It stays there all day as a live reference.

**Phase 1 scope:** Foundation + Briefing + Email + Calendar + People + Search (what we build NOW)
**Future phases:** PR Intelligence, Incident Commander, Food Ordering, Focus Mode, Mini App Dashboard

---

## II. Complete State Matrix

Every possible state the bot can be in, what triggers it, what the user can do, and where it goes next.

```
┌──────────────────┬─────────────────────┬─────────────────────────────┬──────────────────────┐
│ STATE            │ TRIGGER             │ USER CAN DO                 │ TRANSITIONS TO       │
├──────────────────┼─────────────────────┼─────────────────────────────┼──────────────────────┤
│ IDLE             │ Default / any exit  │ Any command, free text      │ → Any state          │
│ ONBOARDING       │ First /start ever   │ Answer setup Q's            │ → IDLE               │
│ BRIEFING         │ /brief, 8:30am job  │ Tap cards, "more", "done"   │ → EMAIL/CAL/IDLE     │
│ EMAIL_LIST       │ /email, briefing→   │ Tap #, "more", "back"       │ → EMAIL_READ/IDLE    │
│ EMAIL_READ       │ Tap email           │ "reply","fwd","archive"     │ → EMAIL_COMPOSE/LIST │
│ EMAIL_COMPOSE    │ "reply"/"new email" │ Type text, "send","cancel"  │ → EMAIL_READ/IDLE    │
│ CALENDAR_DAY     │ /cal, "calendar"    │ Tap meeting, "week","free"  │ → MEETING/CAL_WEEK   │
│ CALENDAR_WEEK    │ "week" from cal     │ Tap day, tap meeting        │ → CAL_DAY/MEETING    │
│ MEETING_DETAIL   │ Tap meeting         │ "prep","decline","join"     │ → CALENDAR_DAY       │
│ MEETING_PREP     │ Auto 5min before    │ "notes","dismiss"           │ → IDLE               │
│ PEOPLE_SEARCH    │ /who, "who is X"    │ Name query                  │ → PEOPLE_DETAIL      │
│ PEOPLE_DETAIL    │ Tap person          │ "org","email","teams"       │ → EMAIL_COMPOSE      │
│ SEARCH           │ /search, "search X" │ Query text                  │ → SEARCH_RESULTS     │
│ SEARCH_RESULTS   │ Search returned     │ Tap result, "more","refine" │ → EMAIL_READ/SEARCH  │
│ PR_LIST          │ /pr, "my PRs"       │ Tap PR, "nudge"             │ → PR_DETAIL          │
│ PR_DETAIL        │ Tap PR              │ "merge","comment","nudge"   │ → PR_LIST            │
│ INCIDENT         │ IcM alert, /inc     │ "ack","analyze","escalate"  │ → INC_ANALYSIS       │
│ INCIDENT_ANALYSIS│ "analyze"           │ "post","edit","dismiss"     │ → IDLE               │
│ FOCUS            │ /focus, "focus 2h"  │ "stop","extend","status"    │ → IDLE (on stop)     │
│ FOOD_ORDER       │ /coffee, "coffee"   │ "go","change","cancel"      │ → FOOD_TRACK/IDLE    │
│ FOOD_TRACKING    │ Order placed        │ "status","cancel"           │ → IDLE (delivered)   │
│ TASKS            │ /tasks, "todo"      │ "add","done #","list"       │ → IDLE               │
│ REMINDER         │ /remind             │ Text + time                 │ → IDLE               │
│ SETTINGS         │ /settings           │ Toggle features             │ → IDLE               │
│ HELP             │ /help               │ Tap category                │ → IDLE               │
│ ERROR            │ Any unhandled error │ "retry","dismiss"           │ → Previous state     │
└──────────────────┴─────────────────────┴─────────────────────────────┴──────────────────────┘
```

**State Transitions Detail:**

```
                    ┌──────────┐
                    │  START   │
                    └────┬─────┘
                         │ /start
                    ┌────▼─────┐      first time?
                    │   IDLE   │◄─────────────────── ONBOARDING
                    └────┬─────┘
          ┌──────────────┼──────────────┬──────────────┐
          │              │              │              │
     /brief         /email         /cal          /search
          │              │              │              │
    ┌─────▼────┐   ┌─────▼─────┐  ┌────▼──────┐  ┌───▼────┐
    │ BRIEFING │   │EMAIL_LIST │  │CALENDAR   │  │SEARCH  │
    └─────┬────┘   └─────┬─────┘  │  _DAY     │  └───┬────┘
          │              │        └────┬──────┘      │
    [tap email]    [tap #N]      [tap meeting]  [tap result]
          │              │              │              │
    ┌─────▼─────┐  ┌────▼──────┐ ┌────▼───────┐     │
    │EMAIL_LIST │  │EMAIL_READ │ │MEETING_    │     │
    └───────────┘  └────┬──────┘ │  DETAIL    │     │
                        │        └────┬───────┘     │
                   [reply]       [prep]             │
                        │              │              │
                  ┌─────▼──────┐ ┌────▼───────┐     │
                  │EMAIL_      │ │MEETING_    │     │
                  │ COMPOSE    │ │  PREP      │     │
                  └────────────┘ └────────────┘     │
                                                    │
                        ┌───────────────────────────┘
                        │
               All states → IDLE (via "back"/"done"/timeout)
```

---

## III. Visual Design System — Donna's Telegram Aesthetic

### 3.1 Response Structure

Every Donna response follows this pattern:

```
◆ DONNA ━━━━━━━━━━━━━━━━━━━━━

[Content — varies by context]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Inline Keyboard Buttons]
```

### 3.2 Card Templates

**Morning Briefing:**
```
◆ DONNA ━━━━━━━━━━━━━━━━━━━━━
☀️ MORNING BRIEFING
Wednesday, April 23 · 8:47 AM

🔴 INCIDENTS
   1 Sev2 on LiveTable — auto-mitigated at 2am
   All clear now

📬 EMAILS (3 need action)
   1. Priya — Design spec sign-off needed
   2. Skip-level — Migration timeline reply
   3. Platform team — Change freeze dates

📅 TODAY (5 meetings · 2h focus time)
   10:30  Standup (15m)
   11:00  1:1 with Manager (30m)
   14:00  Design Review (1h)
   15:00  Sprint Planning (1h)
   16:30  Architecture Sync (30m)

🏃 SPRINT  ████████████░░░  78%
   18/23 done · 2 days left · On track

☁️ 27°C Bangalore · No rain · 35min commute
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Email Card:**
```
📬 EMAIL ━━━━━━━━━━━━━━━━━━━━

From: Priya Sharma
To: Harvey
Date: Apr 23, 10:15 AM
Subject: Design spec — need your sign-off

Priya —

The notification system design spec is ready
for your review. Key decisions:

• Event-sourced approach (not polling)
• Redis for message queue
• MVP ships without retry (v2 adds it)

Need your sign-off by EOD Thursday to stay
on track for sprint commitment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Reply] [Forward] [Archive] [Back]
```

**Meeting Prep Card:**
```
📅 MEETING PREP ━━━━━━━━━━━━━━

1:1 with Manager — in 5 minutes
11:00 AM · Room 4B · 30 min

📋 CONTEXT
• Last 1:1: 2 weeks ago (missed one)
• Your action item: ADR draft — ✅ Done
• Their likely topics: Migration timeline,
  team headcount

💡 TALKING POINTS
• Sprint on track — shipping notification
  MVP Friday
• Flaky test costing ~30min/day in CI
• Alice carrying 60% of reviews — discuss
  load balancing

🔗 Join Teams Meeting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Join Call] [Notes] [Dismiss]
```

**Person Card:**
```
👤 PERSON ━━━━━━━━━━━━━━━━━━━━

Alice Chen
Senior Software Engineer
LiveTable · Platform Team

📍 Bangalore (IST) · 🟢 Available
📧 alicec@microsoft.com
📱 Teams: active

📊 SIGNALS
• Primary owner: auth-service, retry-core
• Reviews cleared same-day (avg 4h)
• 3 open PRs · 2 reviewing
• Last commit: 3 hours ago

🔗 Reports to: Sarah Kim (Principal PM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Send Email] [Teams Chat] [Org Chart] [Back]
```

**Progress Message (live-editing):**
```
◆ DONNA ━━━━━━━━━━━━━━━━━━━━━
⏳ Brewing your briefing...

████░░░░░░░░░░░░  25%
Reading emails...
```
→ Edits to:
```
◆ DONNA ━━━━━━━━━━━━━━━━━━━━━
⏳ Brewing your briefing...

████████░░░░░░░░  50%
Checking calendar...
```
→ Edits to:
```
◆ DONNA ━━━━━━━━━━━━━━━━━━━━━
⏳ Brewing your briefing...

████████████░░░░  75%
Analyzing priorities...
```
→ Replaces with full briefing card

### 3.3 Inline Keyboard Patterns

```python
# Primary actions — full width
[[("📬 Emails (3)", "brief:emails"), ("📅 Calendar", "brief:cal")]]

# Action bar — compact
[
    [("Reply", "email:reply:ID"), ("Forward", "email:fwd:ID"),
     ("Archive", "email:archive:ID")],
    [("◀ Back", "email:back")]
]

# Confirmation
[[("✓ Go", "confirm:yes"), ("✕ Cancel", "confirm:no")]]

# Pagination
[[("◀ Prev", "page:prev"), ("1/5", "noop"), ("Next ▶", "page:next")]]
```

### 3.4 Typography Rules

| Element | Formatting | Example |
|---------|-----------|---------|
| Section header | Bold + emoji prefix | `*📬 EMAILS*` |
| Card title | Bold caps | `*MORNING BRIEFING*` |
| Person name | Bold | `*Alice Chen*` |
| Metadata | Italic | `_Apr 23, 10:15 AM_` |
| Code/commands | Monospace | `` `python -m donna_bot` `` |
| Donna's voice | Plain text with personality | "Your 1:1 is in 5 min. Go crush it." |
| Separator | Unicode box drawing | `━━━━━━━━━━━━━━━━━━━━━━━━━` |
| Status | Emoji indicators | 🟢 Available 🔴 Busy 🟡 Away |

---

## IV. File Structure

```
src/donna_bot/
├── __init__.py                  # Package init, version
├── __main__.py                  # Entry: python -m donna_bot
├── config.py                    # Settings from .env (bot token, feature flags)
├── bot.py                       # Application factory, handler registration
│
├── auth/
│   ├── __init__.py
│   ├── wam.py                   # WAM broker auth (extracted from POC)
│   └── token_manager.py         # Token cache, auto-refresh, error recovery
│
├── graph/
│   ├── __init__.py
│   ├── client.py                # Async Graph HTTP client (httpx)
│   ├── me.py                    # /me (profile, presence, photo)
│   ├── mail.py                  # Mail (list, read, reply, draft, send)
│   ├── calendar.py              # Calendar (today, week, free/busy)
│   ├── people.py                # People (contacts, org, manager, reports)
│   ├── teams.py                 # Teams (chats, messages, channels)
│   ├── search.py                # /search/query (M365 cross-tenant)
│   └── files.py                 # OneDrive/SharePoint files
│
├── handlers/
│   ├── __init__.py
│   ├── start.py                 # /start, /help, onboarding flow
│   ├── briefing.py              # Morning briefing + EOD summary
│   ├── email.py                 # Email conversation handler
│   ├── calendar.py              # Calendar conversation handler
│   ├── people.py                # People lookup handler
│   ├── search.py                # M365 search handler
│   ├── pr.py                    # PR intelligence (Phase 5)
│   ├── food.py                  # Food ordering (Phase 7)
│   ├── focus.py                 # Focus mode (Phase 7)
│   ├── tasks.py                 # Tasks & reminders (Phase 7)
│   ├── incident.py              # Incident commander (Phase 6)
│   └── fallback.py              # Natural language intent router
│
├── formatters/
│   ├── __init__.py
│   ├── escape.py                # MarkdownV2 escaping (tricky!)
│   ├── cards.py                 # Card templates (briefing, email, meeting, person, PR)
│   ├── keyboards.py             # InlineKeyboard builders
│   └── progress.py              # Live-updating progress messages
│
├── scheduler/
│   ├── __init__.py
│   └── jobs.py                  # Proactive jobs (briefing, prep, EOD, nudges)
│
├── state/
│   ├── __init__.py
│   ├── machine.py               # State enum + ConversationHandler factory
│   └── context.py               # Per-user context bag (current data, preferences)
│
├── memory/
│   ├── __init__.py
│   └── store.py                 # SQLite: preferences, patterns, conversation history
│
└── middleware/
    ├── __init__.py
    ├── security.py              # Chat ID whitelist (Harvey only)
    └── logging_mw.py            # Request/response logging

tests/
├── conftest.py                  # Shared fixtures (mock token, mock graph, mock update)
├── test_auth/
│   └── test_token_manager.py
├── test_graph/
│   ├── test_client.py
│   ├── test_mail.py
│   └── test_calendar.py
├── test_formatters/
│   ├── test_escape.py
│   ├── test_cards.py
│   └── test_keyboards.py
├── test_handlers/
│   ├── test_start.py
│   └── test_briefing.py
└── test_state/
    └── test_machine.py
```

---

## V. Phase 1 — Foundation (Tasks 1-8)

### Task 1: Project Setup

**Files:**
- Create: `src/donna_bot/__init__.py`
- Create: `src/donna_bot/__main__.py`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "donna-bot"
version = "0.1.0"
description = "Donna — Harvey's AI concierge, Telegram edition"
requires-python = ">=3.12"
dependencies = [
    "python-telegram-bot[job-queue]>=21.0,<22.0",
    "httpx>=0.27.0",
    "pymsalruntime>=0.17.0",
    "aiosqlite>=0.20.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0",
    "respx>=0.22.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Create .env.example**

```env
# Donna Telegram Bot Configuration
# Copy to .env and fill in values

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=your-bot-token-here

# Harvey's Telegram Chat ID (security: only respond to this user)
HARVEY_CHAT_ID=your-chat-id-here

# Microsoft Graph Auth
GRAPH_APP_ID=d3590ed6-52b3-4102-aeff-aad2292ab01c
GRAPH_TENANT_ID=72f988bf-86f1-41af-91ab-2d7cd011db47

# Feature Flags (1=on, 0=off)
FEATURE_BRIEFING=1
FEATURE_EMAIL=1
FEATURE_CALENDAR=1
FEATURE_PEOPLE=1
FEATURE_SEARCH=1
FEATURE_PR=0
FEATURE_FOOD=0
FEATURE_FOCUS=0

# Schedule (24h format, IST)
BRIEFING_HOUR=8
BRIEFING_MINUTE=30
EOD_HOUR=18
EOD_MINUTE=30
```

- [ ] **Step 3: Create package init**

```python
# src/donna_bot/__init__.py
"""Donna — Harvey's AI concierge. Telegram edition."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create entry point**

```python
# src/donna_bot/__main__.py
"""Entry point: python -m donna_bot"""

import asyncio
import sys

from donna_bot.bot import create_app


def main() -> None:
    print("\n◆ DONNA ━━━━━━━━━━━━━━━━━━━━━")
    print("  Starting Telegram Bot v0.1")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    app = create_app()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create test conftest with shared fixtures**

```python
# tests/conftest.py
"""Shared test fixtures for Donna Bot tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_token() -> str:
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkZha2VUb2tlbiJ9.test.signature"


@pytest.fixture
def mock_graph_response() -> dict:
    """Standard Graph API response envelope."""
    return {"value": [], "@odata.count": 0}


@pytest.fixture
def mock_update() -> MagicMock:
    """Mock Telegram Update object."""
    update = MagicMock()
    update.effective_chat.id = 12345678
    update.effective_user.first_name = "Harvey"
    update.effective_user.id = 12345678
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_markdown_v2 = AsyncMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Mock Telegram CallbackContext."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    context.bot.send_chat_action = AsyncMock()
    context.user_data = {}
    context.job_queue = MagicMock()
    return context
```

- [ ] **Step 6: Install dependencies**

Run: `cd src && pip install -e ".[dev]"`
Expected: All packages install successfully

- [ ] **Step 7: Verify test framework**

Run: `pytest tests/ -v --co`
Expected: conftest.py collected, 0 tests (fixtures available)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .env.example src/donna_bot/__init__.py src/donna_bot/__main__.py tests/conftest.py
git commit -m "feat(bot): project scaffold — pyproject.toml, entry point, test fixtures"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `src/donna_bot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test for config loading**

```python
# tests/test_config.py
"""Tests for configuration loading."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from donna_bot.config import Settings


class TestSettings:
    def test_loads_from_env(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "test-token-123",
            "HARVEY_CHAT_ID": "99887766",
            "GRAPH_APP_ID": "d3590ed6-test",
            "GRAPH_TENANT_ID": "72f988bf-test",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.telegram_token == "test-token-123"
            assert s.harvey_chat_id == 99887766
            assert s.graph_app_id == "d3590ed6-test"

    def test_missing_token_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
                Settings.from_env()

    def test_feature_flags_default_on(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "t",
            "HARVEY_CHAT_ID": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.feature_briefing is True
            assert s.feature_email is True
            assert s.feature_pr is False  # default off

    def test_schedule_defaults(self) -> None:
        env = {
            "TELEGRAM_BOT_TOKEN": "t",
            "HARVEY_CHAT_ID": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            s = Settings.from_env()
            assert s.briefing_hour == 8
            assert s.briefing_minute == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'donna_bot.config'`

- [ ] **Step 3: Implement config module**

```python
# src/donna_bot/config.py
"""Configuration — loads from .env file and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise ValueError(f"Missing required env var: {key}. Copy .env.example → .env and fill in values.")
    return val


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(int(default))) == "1"


def _env_int(key: str, default: int = 0) -> int:
    return int(os.environ.get(key, str(default)))


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_token: str
    harvey_chat_id: int

    # Graph Auth
    graph_app_id: str = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
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
            graph_app_id=_env("GRAPH_APP_ID", "d3590ed6-52b3-4102-aeff-aad2292ab01c"),
            graph_tenant_id=_env("GRAPH_TENANT_ID", "72f988bf-86f1-41af-91ab-2d7cd011db47"),
            feature_briefing=_env_bool("FEATURE_BRIEFING", True),
            feature_email=_env_bool("FEATURE_EMAIL", True),
            feature_calendar=_env_bool("FEATURE_CALENDAR", True),
            feature_people=_env_bool("FEATURE_PEOPLE", True),
            feature_search=_env_bool("FEATURE_SEARCH", True),
            feature_pr=_env_bool("FEATURE_PR", False),
            feature_food=_env_bool("FEATURE_FOOD", False),
            feature_focus=_env_bool("FEATURE_FOCUS", False),
            briefing_hour=_env_int("BRIEFING_HOUR", 8),
            briefing_minute=_env_int("BRIEFING_MINUTE", 30),
            eod_hour=_env_int("EOD_HOUR", 18),
            eod_minute=_env_int("EOD_MINUTE", 30),
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/donna_bot/config.py tests/test_config.py
git commit -m "feat(bot): config module — .env loading, feature flags, schedule"
```

---

### Task 3: WAM Auth Module

**Files:**
- Create: `src/donna_bot/auth/__init__.py`
- Create: `src/donna_bot/auth/wam.py`
- Create: `src/donna_bot/auth/token_manager.py`
- Test: `tests/test_auth/test_token_manager.py`

- [ ] **Step 1: Write failing test for token manager**

```python
# tests/test_auth/__init__.py
# (empty)
```

```python
# tests/test_auth/test_token_manager.py
"""Tests for token management."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from donna_bot.auth.token_manager import TokenManager


class TestTokenManager:
    def test_no_token_initially(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        assert tm.has_valid_token is False

    def test_set_token_marks_valid(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=3600)
        assert tm.has_valid_token is True
        assert tm.access_token == "abc123"

    def test_expired_token_invalid(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=-10)  # already expired
        assert tm.has_valid_token is False

    def test_token_near_expiry_triggers_refresh(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=60)  # expires in 60s
        assert tm.needs_refresh is True  # within 5min buffer

    def test_token_with_long_expiry_no_refresh(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("abc123", expires_in=3600)  # 1 hour
        assert tm.needs_refresh is False

    def test_headers_returns_bearer(self) -> None:
        tm = TokenManager(app_id="test", tenant_id="test")
        tm.set_token("mytoken", expires_in=3600)
        h = tm.auth_headers
        assert h["Authorization"] == "Bearer mytoken"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth/test_token_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement WAM auth (extract from POC)**

```python
# src/donna_bot/auth/__init__.py
"""Authentication — WAM broker for Microsoft Graph."""

from donna_bot.auth.token_manager import TokenManager

__all__ = ["TokenManager"]
```

```python
# src/donna_bot/auth/wam.py
"""WAM Broker authentication — Windows SSO for Graph tokens.

Extracted from poc/graph_probe.py. This ONLY works on Windows with
an active Microsoft corp SSO session. For cloud deployment, swap
this module for client_credentials.py (future).
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

# Sentinel for environments without WAM (CI, Linux, macOS)
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

    # Step 1: Discover Windows SSO accounts
    event = threading.Event()
    disc_result: list = [None]

    def disc_cb(r: object) -> None:
        disc_result[0] = r
        event.set()

    pymsalruntime.discover_accounts(
        app_id, "00000000-0000-0000-0000-000000000001", disc_cb,
    )
    event.wait(timeout)

    if not disc_result[0]:
        logger.error("No Windows SSO accounts found")
        return None, 0

    # Find Microsoft corp account
    ms_account = None
    for a in disc_result[0].get_accounts():
        if "microsoft.com" in a.get_user_name():
            ms_account = a
            break

    if not ms_account:
        logger.error("No Microsoft corp account in Windows SSO")
        return None, 0

    logger.info("Found SSO account: %s", ms_account.get_user_name())

    # Step 2: Acquire token silently
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
        params, "00000000-0000-0000-0000-000000000002", ms_account, tok_cb,
    )
    event2.wait(timeout)

    r = tok_result[0]
    if r:
        token = r.get_access_token()
        if token and len(token) > 50:
            logger.info("Token acquired via WAM broker")
            # WAM tokens typically expire in 3600s (1h)
            return token, 3600
        else:
            error = (r.get_error() or "empty token")[:200]
            logger.error("WAM token error: %s", error)

    return None, 0
```

```python
# src/donna_bot/auth/token_manager.py
"""Token manager — caches Graph tokens with auto-refresh."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# Refresh token 5 minutes before expiry
_REFRESH_BUFFER_SECS = 300


class TokenManager:
    """Manages Graph API access tokens with caching and refresh."""

    def __init__(self, app_id: str, tenant_id: str) -> None:
        self.app_id = app_id
        self.tenant_id = tenant_id
        self._token: str | None = None
        self._expires_at: float = 0.0

    def set_token(self, token: str, expires_in: int) -> None:
        self._token = token
        self._expires_at = time.monotonic() + expires_in

    @property
    def has_valid_token(self) -> bool:
        return self._token is not None and time.monotonic() < self._expires_at

    @property
    def needs_refresh(self) -> bool:
        if self._token is None:
            return True
        return time.monotonic() > (self._expires_at - _REFRESH_BUFFER_SECS)

    @property
    def access_token(self) -> str | None:
        if self.has_valid_token:
            return self._token
        return None

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def ensure_token(self) -> str:
        """Get a valid token, refreshing via WAM if needed.

        Raises RuntimeError if no token can be acquired.
        """
        if self.has_valid_token and not self.needs_refresh:
            return self._token  # type: ignore[return-value]

        from donna_bot.auth.wam import acquire_token_wam

        token, expires_in = acquire_token_wam(self.app_id, self.tenant_id)
        if token:
            self.set_token(token, expires_in)
            return token

        # If we still have a valid (but soon-expiring) token, use it
        if self.has_valid_token:
            logger.warning("WAM refresh failed — using existing token (expires soon)")
            return self._token  # type: ignore[return-value]

        raise RuntimeError(
            "Cannot acquire Graph token. Is Harvey's Windows session active?"
        )

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_auth/test_token_manager.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/donna_bot/auth/ tests/test_auth/
git commit -m "feat(bot): WAM auth module — token manager with cache + auto-refresh"
```

---

### Task 4: Async Graph Client

**Files:**
- Create: `src/donna_bot/graph/__init__.py`
- Create: `src/donna_bot/graph/client.py`
- Test: `tests/test_graph/test_client.py`

- [ ] **Step 1: Write failing test for Graph client**

```python
# tests/test_graph/__init__.py
# (empty)
```

```python
# tests/test_graph/test_client.py
"""Tests for async Graph client."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx

from donna_bot.graph.client import GraphClient

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@pytest.fixture
def graph_client(mock_token: str) -> GraphClient:
    tm = MagicMock()
    tm.ensure_token.return_value = mock_token
    tm.auth_headers = {"Authorization": f"Bearer {mock_token}", "Content-Type": "application/json"}
    return GraphClient(token_manager=tm)


class TestGraphClient:
    @respx.mock
    async def test_get_me(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me").mock(
            return_value=httpx.Response(200, json={
                "displayName": "Harvey Gupta",
                "mail": "harvey@microsoft.com",
            })
        )
        data = await graph_client.get("/me")
        assert data["displayName"] == "Harvey Gupta"

    @respx.mock
    async def test_get_with_params(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me/messages").mock(
            return_value=httpx.Response(200, json={"value": [{"subject": "Test"}]})
        )
        data = await graph_client.get("/me/messages", params={"$top": "5"})
        assert len(data["value"]) == 1

    @respx.mock
    async def test_post_search(self, graph_client: GraphClient) -> None:
        respx.post(f"{GRAPH_BASE}/search/query").mock(
            return_value=httpx.Response(200, json={"value": []})
        )
        data = await graph_client.post("/search/query", json={"requests": []})
        assert data["value"] == []

    @respx.mock
    async def test_handles_401_gracefully(self, graph_client: GraphClient) -> None:
        respx.get(f"{GRAPH_BASE}/me").mock(
            return_value=httpx.Response(401, json={"error": {"message": "Unauthorized"}})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await graph_client.get("/me")

    @respx.mock
    async def test_handles_throttling_429(self, graph_client: GraphClient) -> None:
        route = respx.get(f"{GRAPH_BASE}/me")
        route.side_effect = [
            httpx.Response(429, headers={"Retry-After": "1"}, json={"error": {"message": "Throttled"}}),
            httpx.Response(200, json={"displayName": "Harvey"}),
        ]
        data = await graph_client.get("/me")
        assert data["displayName"] == "Harvey"
        assert route.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_graph/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement async Graph client**

```python
# src/donna_bot/graph/__init__.py
"""Microsoft Graph API — async client and domain modules."""

from donna_bot.graph.client import GraphClient

__all__ = ["GraphClient"]
```

```python
# src/donna_bot/graph/client.py
"""Async Microsoft Graph API client using httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from donna_bot.auth.token_manager import TokenManager

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MAX_RETRIES = 3
TIMEOUT = 30.0


class GraphClient:
    """Async HTTP client for Microsoft Graph API."""

    def __init__(self, token_manager: TokenManager) -> None:
        self._tm = token_manager
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=GRAPH_BASE,
                timeout=TIMEOUT,
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        self._tm.ensure_token()
        return self._tm.auth_headers

    async def get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """GET request to Graph API with retry on 429."""
        client = await self._ensure_client()

        for attempt in range(MAX_RETRIES):
            resp = await client.get(path, headers=self._headers(), params=params)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("Throttled (429) — retrying in %ds", retry_after)
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json()

        resp.raise_for_status()
        return {}  # unreachable

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST request to Graph API."""
        client = await self._ensure_client()

        for attempt in range(MAX_RETRIES):
            resp = await client.post(path, headers=self._headers(), json=json)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "2"))
                logger.warning("Throttled (429) — retrying in %ds", retry_after)
                await asyncio.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json()

        resp.raise_for_status()
        return {}

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_graph/test_client.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/donna_bot/graph/ tests/test_graph/
git commit -m "feat(bot): async Graph client — httpx, retry on 429, token refresh"
```

---

### Task 5: MarkdownV2 Formatter + Card Templates

**Files:**
- Create: `src/donna_bot/formatters/__init__.py`
- Create: `src/donna_bot/formatters/escape.py`
- Create: `src/donna_bot/formatters/cards.py`
- Create: `src/donna_bot/formatters/progress.py`
- Test: `tests/test_formatters/test_escape.py`
- Test: `tests/test_formatters/test_cards.py`

- [ ] **Step 1: Write failing test for MarkdownV2 escape**

```python
# tests/test_formatters/__init__.py
# (empty)
```

```python
# tests/test_formatters/test_escape.py
"""Tests for MarkdownV2 escaping — this is notoriously tricky."""

from __future__ import annotations

from donna_bot.formatters.escape import md2, md2_bold, md2_italic, md2_code, md2_link, md2_pre


class TestMd2Escape:
    def test_escapes_special_chars(self) -> None:
        assert md2("Hello.World!") == r"Hello\.World\!"

    def test_preserves_plain_text(self) -> None:
        assert md2("Hello World") == "Hello World"

    def test_escapes_all_special(self) -> None:
        result = md2("test_value (1.0) [v2] {a} ~x~ `c` >q #h +p -m =e |p")
        # All of _()[]{}~`>#+-=|.! must be escaped
        assert "\\_" in result
        assert "\\(" in result
        assert "\\." in result

    def test_bold(self) -> None:
        assert md2_bold("Hello") == "*Hello*"

    def test_italic(self) -> None:
        assert md2_italic("Hello") == "_Hello_"

    def test_code(self) -> None:
        assert md2_code("print()") == "`print\\(\\)`"

    def test_link(self) -> None:
        result = md2_link("Click", "https://example.com/path?q=1")
        assert result.startswith("[Click]")
        assert "https://example\\.com" in result

    def test_pre_block(self) -> None:
        result = md2_pre("line1\nline2")
        assert result.startswith("```\n")
        assert result.endswith("\n```")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatters/test_escape.py -v`
Expected: FAIL

- [ ] **Step 3: Implement MarkdownV2 escape utilities**

```python
# src/donna_bot/formatters/__init__.py
"""Formatters — MarkdownV2, card templates, keyboards, progress."""
```

```python
# src/donna_bot/formatters/escape.py
"""MarkdownV2 escaping — Telegram's most annoying format.

Telegram MarkdownV2 requires escaping these characters OUTSIDE of
code/pre blocks: _ * [ ] ( ) ~ ` > # + - = | { } . !

Inside code blocks, only ` and \\ need escaping.
Inside links, only ) and \\ need escaping inside the URL.
"""

from __future__ import annotations

import re

# Characters that must be escaped in MarkdownV2 text
_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def md2(text: str) -> str:
    """Escape text for MarkdownV2 — all special chars backslashed."""
    return _SPECIAL.sub(r"\\\1", text)


def md2_bold(text: str) -> str:
    """Bold text — *text* (text is auto-escaped)."""
    return f"*{md2(text)}*"


def md2_italic(text: str) -> str:
    """Italic text — _text_ (text is auto-escaped)."""
    return f"_{md2(text)}_"


def md2_code(text: str) -> str:
    """Inline code — `text` (special chars escaped)."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`")
    escaped = _SPECIAL.sub(r"\\\1", escaped)
    return f"`{escaped}`"


def md2_pre(text: str, language: str = "") -> str:
    """Code block — ```text``` (minimal escaping inside)."""
    # Inside pre blocks, only ` and \ need escaping
    inner = text.replace("\\", "\\\\").replace("`", "\\`")
    if language:
        return f"```{language}\n{inner}\n```"
    return f"```\n{inner}\n```"


def md2_link(label: str, url: str) -> str:
    """Markdown link — [label](url)."""
    escaped_label = md2(label)
    # Inside link URL, only ) and \ need escaping
    escaped_url = url.replace("\\", "\\\\").replace(")", "\\)")
    # But the URL itself still needs . escaped for MarkdownV2
    escaped_url = escaped_url.replace(".", "\\.")
    return f"[{escaped_label}]({escaped_url})"


def md2_separator() -> str:
    """Visual separator line."""
    return md2("━" * 30)


def md2_header(title: str) -> str:
    """Donna-style header: ◆ DONNA ━━━━━━━━━━━━━━━━"""
    return f"◆ {md2_bold('DONNA')} {md2('━' * 22)}"


def md2_section(emoji: str, title: str) -> str:
    """Section header: 📬 EMAILS"""
    return f"{emoji} {md2_bold(title)}"


def md2_progress_bar(current: int, total: int, width: int = 15) -> str:
    """Progress bar: ████████░░░░ 67%"""
    if total == 0:
        return md2("░" * width + " 0%")
    pct = min(current / total, 1.0)
    filled = int(width * pct)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return md2(f"{bar}  {current}/{total} ({int(pct * 100)}%)")
```

- [ ] **Step 4: Run escape tests**

Run: `pytest tests/test_formatters/test_escape.py -v`
Expected: All passed

- [ ] **Step 5: Write failing test for card templates**

```python
# tests/test_formatters/test_cards.py
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
        assert "All clear" in result or "No incidents" in result


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
        assert "notification system" in result


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
```

- [ ] **Step 6: Implement card templates**

```python
# src/donna_bot/formatters/cards.py
"""Card templates — beautiful, structured messages for Donna's responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from donna_bot.formatters.escape import (
    md2,
    md2_bold,
    md2_header,
    md2_italic,
    md2_link,
    md2_progress_bar,
    md2_section,
    md2_separator,
)


def format_briefing_card(
    incidents: list[dict],
    emails: list[dict],
    meetings: list[dict],
    sprint: dict[str, int],
    weather: dict[str, Any] | None = None,
) -> str:
    """Morning briefing — the crown jewel."""
    now = datetime.now()
    lines = [
        md2_header(""),
        f"☀️ {md2_bold('MORNING BRIEFING')}",
        md2_italic(now.strftime("%A, %B %d · %I:%M %p")),
        "",
    ]

    # Incidents
    if incidents:
        lines.append(f"🔴 {md2_bold('INCIDENTS')}")
        for inc in incidents:
            sev = md2(inc.get("severity", "?"))
            title = md2(inc.get("title", "Unknown"))
            status = md2(inc.get("status", "active"))
            lines.append(f"   {sev} {title} — {status}")
    else:
        lines.append(f"🟢 {md2_bold('INCIDENTS')}  {md2('All clear')}")
    lines.append("")

    # Emails
    count = len(emails)
    label = f"{count} need action" if count > 0 else "Inbox zero"
    lines.append(f"📬 {md2_bold('EMAILS')} {md2('(' + label + ')')}")
    for i, em in enumerate(emails[:5], 1):
        sender = md2(em.get("from", "?"))
        subject = md2(em.get("subject", "(no subject)"))
        lines.append(f"   {md2(str(i) + '.')} {sender} — {subject}")
    lines.append("")

    # Meetings
    focus_hours = _calc_focus_time(meetings)
    meeting_label = f"{len(meetings)} meetings · {focus_hours}h focus time"
    lines.append(f"📅 {md2_bold('TODAY')} {md2('(' + meeting_label + ')')}")
    for m in meetings[:6]:
        start = md2(m.get("start", "?"))
        subj = md2(m.get("subject", "?"))
        dur = md2(m.get("duration", ""))
        lines.append(f"   {start}  {subj} {md2_italic('(' + dur + ')')}" if dur else f"   {start}  {subj}")
    lines.append("")

    # Sprint
    done = sprint.get("done", 0)
    total = sprint.get("total", 0)
    lines.append(f"🏃 {md2_bold('SPRINT')}  {md2_progress_bar(done, total)}")
    lines.append("")

    # Weather
    if weather:
        temp = weather.get("temp", "?")
        cond = weather.get("condition", "")
        commute = weather.get("commute", "")
        lines.append(f"☁️ {md2(f'{temp}°C · {cond} · {commute} commute')}")
        lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def format_email_card(
    sender: str,
    to: str,
    date: str,
    subject: str,
    body: str,
    has_attachments: bool = False,
) -> str:
    """Single email display — full message."""
    lines = [
        f"📬 {md2_bold('EMAIL')} {md2('━' * 22)}",
        "",
        f"{md2_bold('From:')} {md2(sender)}",
        f"{md2_bold('To:')} {md2(to)}",
        f"{md2_bold('Date:')} {md2_italic(date)}",
        f"{md2_bold('Subject:')} {md2(subject)}",
    ]
    if has_attachments:
        lines.append(f"📎 {md2_italic('Has attachments')}")
    lines.extend(["", md2(body[:2000]), "", md2_separator()])
    return "\n".join(lines)


def format_meeting_card(
    subject: str,
    time: str,
    duration: str,
    location: str | None = None,
    attendees: list[str] | None = None,
    context: str | None = None,
    talking_points: list[str] | None = None,
    join_url: str | None = None,
) -> str:
    """Meeting prep card — context + talking points."""
    lines = [
        f"📅 {md2_bold('MEETING PREP')} {md2('━' * 16)}",
        "",
        md2_bold(subject),
        f"{md2(time)} · {md2(duration)}",
    ]
    if location:
        lines.append(f"📍 {md2(location)}")
    if attendees:
        names = ", ".join(attendees[:5])
        lines.append(f"👥 {md2(names)}")
    lines.append("")

    if context:
        lines.append(f"📋 {md2_bold('CONTEXT')}")
        lines.append(f"  {md2(context)}")
        lines.append("")

    if talking_points:
        lines.append(f"💡 {md2_bold('TALKING POINTS')}")
        for tp in talking_points:
            lines.append(f"  • {md2(tp)}")
        lines.append("")

    if join_url:
        lines.append(f"🔗 {md2_link('Join Teams Meeting', join_url)}")
        lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def format_person_card(
    name: str,
    title: str,
    department: str | None = None,
    location: str | None = None,
    availability: str | None = None,
    email: str | None = None,
    manager: str | None = None,
) -> str:
    """Person card — who is X."""
    avail_emoji = {"Available": "🟢", "Busy": "🔴", "Away": "🟡",
                   "DoNotDisturb": "⛔", "Offline": "⚪"}.get(availability or "", "⚪")

    lines = [
        f"👤 {md2_bold('PERSON')} {md2('━' * 22)}",
        "",
        md2_bold(name),
        md2_italic(title),
    ]
    if department:
        lines.append(md2(department))
    lines.append("")

    if location or availability:
        parts = []
        if location:
            parts.append(f"📍 {md2(location)}")
        if availability:
            parts.append(f"{avail_emoji} {md2(availability)}")
        lines.append(" · ".join(parts))

    if email:
        lines.append(f"📧 {md2(email)}")

    if manager:
        lines.append(f"🔗 {md2('Reports to: ' + manager)}")

    lines.extend(["", md2_separator()])
    return "\n".join(lines)


def format_email_list(emails: list[dict], page: int = 1, total: int = 0) -> str:
    """Email list — compact view of inbox."""
    lines = [
        f"📬 {md2_bold('INBOX')} {md2('━' * 24)}",
        md2_italic(f"Showing {len(emails)} of {total}"),
        "",
    ]
    for i, em in enumerate(emails, 1):
        sender = md2(em.get("from", "?"))
        subject = md2(em.get("subject", "(no subject)")[:50])
        is_read = em.get("isRead", True)
        indicator = "●" if not is_read else "○"
        lines.append(f"  {md2(indicator)} {md2_bold(str(i))}\\. {sender}")
        lines.append(f"     {subject}")
        lines.append("")

    lines.append(md2_separator())
    return "\n".join(lines)


def _calc_focus_time(meetings: list[dict]) -> int:
    """Rough estimate of focus hours based on meeting count."""
    meeting_hours = len(meetings) * 0.75  # avg 45min per meeting
    return max(0, int(8 - meeting_hours))
```

```python
# src/donna_bot/formatters/progress.py
"""Live-updating progress messages — the typing dance."""

from __future__ import annotations

from donna_bot.formatters.escape import md2, md2_bold, md2_header


def progress_message(step: str, percent: int) -> str:
    """Generate a progress message for live-editing.

    Usage: Send once, then edit_message_text with updated step/percent.
    """
    width = 15
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty

    return "\n".join([
        md2_header(""),
        f"⏳ {md2_bold('Brewing your briefing' + '.' * (percent // 30 + 1))}",
        "",
        md2(f"{bar}  {percent}%"),
        md2_italic(step),
    ])
```

- [ ] **Step 7: Run all formatter tests**

Run: `pytest tests/test_formatters/ -v`
Expected: All passed

- [ ] **Step 8: Commit**

```bash
git add src/donna_bot/formatters/ tests/test_formatters/
git commit -m "feat(bot): MarkdownV2 formatters — escape, cards, progress animation"
```

---

### Task 6: Inline Keyboard Builders

**Files:**
- Create: `src/donna_bot/formatters/keyboards.py`
- Test: `tests/test_formatters/test_keyboards.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_formatters/test_keyboards.py
"""Tests for inline keyboard builders."""

from __future__ import annotations

from donna_bot.formatters.keyboards import (
    briefing_keyboard,
    email_action_keyboard,
    email_list_keyboard,
    confirm_keyboard,
    pagination_keyboard,
)


class TestKeyboards:
    def test_briefing_keyboard_has_sections(self) -> None:
        kb = briefing_keyboard(email_count=3, meeting_count=5)
        # Should have email and calendar buttons
        flat = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("Email" in t for t in flat)
        assert any("Calendar" in t for t in flat)

    def test_email_action_keyboard(self) -> None:
        kb = email_action_keyboard(email_id="AAMk123")
        flat = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert any("reply" in d for d in flat)
        assert any("archive" in d for d in flat)

    def test_email_list_keyboard(self) -> None:
        emails = [{"id": f"id{i}", "from": f"Person {i}"} for i in range(5)]
        kb = email_list_keyboard(emails)
        assert len(kb.inline_keyboard) >= 5  # one row per email

    def test_confirm_keyboard(self) -> None:
        kb = confirm_keyboard(action="send_email")
        flat = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "✓ Go" in flat or "✓ Confirm" in flat
        assert "✕ Cancel" in flat

    def test_pagination_keyboard(self) -> None:
        kb = pagination_keyboard(prefix="email", page=2, total_pages=5)
        flat = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("◀" in t for t in flat)
        assert any("▶" in t for t in flat)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_formatters/test_keyboards.py -v`
Expected: FAIL

- [ ] **Step 3: Implement keyboard builders**

```python
# src/donna_bot/formatters/keyboards.py
"""Inline keyboard builders — Donna's interactive controls."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def briefing_keyboard(email_count: int = 0, meeting_count: int = 0) -> InlineKeyboardMarkup:
    """Keyboard for the morning briefing card."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"📬 Emails ({email_count})", callback_data="brief:emails"),
            InlineKeyboardButton(f"📅 Calendar ({meeting_count})", callback_data="brief:cal"),
        ],
        [
            InlineKeyboardButton("🔍 Search", callback_data="brief:search"),
            InlineKeyboardButton("👤 People", callback_data="brief:people"),
        ],
        [
            InlineKeyboardButton("☕ Coffee", callback_data="brief:coffee"),
            InlineKeyboardButton("⚙️ Settings", callback_data="brief:settings"),
        ],
    ])


def email_list_keyboard(emails: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard for email list — one button per email."""
    rows = []
    for i, em in enumerate(emails[:10], 1):
        sender = em.get("from", "?")[:20]
        eid = em.get("id", "")
        rows.append([InlineKeyboardButton(f"{i}. {sender}", callback_data=f"email:read:{eid}")])

    rows.append([
        InlineKeyboardButton("📥 More", callback_data="email:more"),
        InlineKeyboardButton("◀ Back", callback_data="nav:back"),
    ])
    return InlineKeyboardMarkup(rows)


def email_action_keyboard(email_id: str) -> InlineKeyboardMarkup:
    """Action buttons for a single email."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("↩️ Reply", callback_data=f"email:reply:{email_id}"),
            InlineKeyboardButton("↪️ Forward", callback_data=f"email:fwd:{email_id}"),
            InlineKeyboardButton("📦 Archive", callback_data=f"email:archive:{email_id}"),
        ],
        [InlineKeyboardButton("◀ Back to Inbox", callback_data="email:list")],
    ])


def meeting_action_keyboard(meeting_id: str, join_url: str | None = None) -> InlineKeyboardMarkup:
    """Action buttons for a meeting card."""
    rows = []
    if join_url:
        rows.append([InlineKeyboardButton("🔗 Join Call", url=join_url)])
    rows.append([
        InlineKeyboardButton("📋 Notes", callback_data=f"meet:notes:{meeting_id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"meet:decline:{meeting_id}"),
    ])
    rows.append([InlineKeyboardButton("◀ Back", callback_data="nav:back")])
    return InlineKeyboardMarkup(rows)


def person_action_keyboard(email: str) -> InlineKeyboardMarkup:
    """Action buttons for a person card."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📧 Email", callback_data=f"person:email:{email}"),
            InlineKeyboardButton("💬 Teams", callback_data=f"person:teams:{email}"),
        ],
        [
            InlineKeyboardButton("🏢 Org Chart", callback_data=f"person:org:{email}"),
            InlineKeyboardButton("◀ Back", callback_data="nav:back"),
        ],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Simple confirm/cancel."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✓ Confirm", callback_data=f"confirm:yes:{action}"),
            InlineKeyboardButton("✕ Cancel", callback_data=f"confirm:no:{action}"),
        ],
    ])


def pagination_keyboard(prefix: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Prev/Next pagination."""
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("◀ Prev", callback_data=f"{prefix}:page:{page - 1}"))
    buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ▶", callback_data=f"{prefix}:page:{page + 1}"))
    return InlineKeyboardMarkup([buttons])
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_formatters/test_keyboards.py -v`
Expected: All passed

- [ ] **Step 5: Commit**

```bash
git add src/donna_bot/formatters/keyboards.py tests/test_formatters/test_keyboards.py
git commit -m "feat(bot): inline keyboard builders — briefing, email, meeting, person, pagination"
```

---

### Task 7: Security Middleware

**Files:**
- Create: `src/donna_bot/middleware/__init__.py`
- Create: `src/donna_bot/middleware/security.py`
- Create: `src/donna_bot/middleware/logging_mw.py`

- [ ] **Step 1: Implement security middleware (Harvey-only access)**

```python
# src/donna_bot/middleware/__init__.py
"""Middleware — security, logging."""
```

```python
# src/donna_bot/middleware/security.py
"""Security — whitelist Harvey's chat ID. No one else talks to Donna."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Coroutine

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

_AUTHORIZED_CHAT_ID: int | None = None


def set_authorized_chat_id(chat_id: int) -> None:
    global _AUTHORIZED_CHAT_ID
    _AUTHORIZED_CHAT_ID = chat_id


def harvey_only(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator: only allow Harvey's chat ID through.

    Anyone else gets a polite but firm rejection.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> Any:
        chat_id = update.effective_chat.id if update.effective_chat else None

        if _AUTHORIZED_CHAT_ID and chat_id != _AUTHORIZED_CHAT_ID:
            logger.warning("Unauthorized access attempt from chat_id=%s", chat_id)
            if update.message:
                await update.message.reply_text(
                    "I'm Donna. I only work for Harvey. "
                    "You seem nice, but I'm not your assistant."
                )
            return None

        return await func(update, context, *args, **kwargs)

    return wrapper
```

```python
# src/donna_bot/middleware/logging_mw.py
"""Logging middleware — structured request/response logging."""

from __future__ import annotations

import logging
import time
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("donna_bot")


async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming update — called before handlers."""
    if update.message and update.message.text:
        user = update.effective_user
        logger.info(
            "[%s] %s: %s",
            update.update_id,
            user.first_name if user else "?",
            update.message.text[:100],
        )
    elif update.callback_query:
        logger.info(
            "[%s] Callback: %s",
            update.update_id,
            update.callback_query.data,
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/donna_bot/middleware/
git commit -m "feat(bot): security middleware — Harvey-only access + request logging"
```

---

### Task 8: Bot Application Shell + /start + /help

**Files:**
- Create: `src/donna_bot/bot.py`
- Create: `src/donna_bot/handlers/__init__.py`
- Create: `src/donna_bot/handlers/start.py`
- Create: `src/donna_bot/state/__init__.py`
- Create: `src/donna_bot/state/machine.py`
- Test: `tests/test_handlers/test_start.py`

- [ ] **Step 1: Write failing test for /start handler**

```python
# tests/test_handlers/__init__.py
# (empty)
```

```python
# tests/test_handlers/test_start.py
"""Tests for /start and /help handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from donna_bot.handlers.start import start_command, help_command


class TestStartCommand:
    async def test_start_sends_welcome(self, mock_update: MagicMock, mock_context: MagicMock) -> None:
        with patch("donna_bot.handlers.start._AUTHORIZED_CHAT_ID", mock_update.effective_chat.id):
            await start_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            text = mock_update.message.reply_text.call_args[1].get("text", "")
            assert "Donna" in text or "DONNA" in text

    async def test_help_lists_commands(self, mock_update: MagicMock, mock_context: MagicMock) -> None:
        await help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        text = mock_update.message.reply_text.call_args[1].get("text", "")
        assert "brief" in text.lower() or "email" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_handlers/test_start.py -v`
Expected: FAIL

- [ ] **Step 3: Implement state machine enum**

```python
# src/donna_bot/state/__init__.py
"""State management — conversation state machine."""
```

```python
# src/donna_bot/state/machine.py
"""Conversation states — the full Donna state matrix."""

from enum import IntEnum, auto


class State(IntEnum):
    """Every state Donna's conversation can be in."""
    IDLE = auto()
    ONBOARDING = auto()

    # Briefing flow
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

    # Search flow
    SEARCH = auto()
    SEARCH_RESULTS = auto()

    # PR flow
    PR_LIST = auto()
    PR_DETAIL = auto()

    # Incident flow
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
```

- [ ] **Step 4: Implement /start and /help handlers**

```python
# src/donna_bot/handlers/__init__.py
"""Handlers — one module per capability domain."""
```

```python
# src/donna_bot/handlers/start.py
"""Start and help handlers — Donna's first impression."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from donna_bot.formatters.escape import md2, md2_bold, md2_italic, md2_separator
from donna_bot.formatters.keyboards import briefing_keyboard
from donna_bot.middleware.security import harvey_only

logger = logging.getLogger(__name__)

_AUTHORIZED_CHAT_ID: int | None = None

WELCOME_TEXT = """
◆ {bold_donna} ━━━━━━━━━━━━━━━━━━━━━

Hey Harvey\\.

I'm awake\\. Your calendar, inbox, org chart,
sprint board — I can see all of it\\.

{italic_tagline}

Here's what I can do:

📬  /email — Your inbox, triaged
📅  /cal — Today's meetings \\+ prep
☀️  /brief — Full morning briefing
🔍  /search — Search everything in M365
👤  /who — People \\+ org chart
⚙️  /settings — Customize me
❓  /help — All commands

{italic_ready}

{separator}
""".strip()

HELP_TEXT = """
◆ {bold_donna} ━━━━━━━━━━━━━━━━━━━━━
❓ {bold_commands}

{bold_daily}
  /brief — Morning briefing \\(emails, cal, sprint\\)
  /email — Inbox triage \\(top emails, read, reply\\)
  /cal — Calendar \\(today, week, free time\\)

{bold_people}
  /who \\<name\\> — Look up anyone in the org
  /search \\<query\\> — Search all of M365

{bold_eng}
  /pr — Your pull requests
  /incident — Active incidents

{bold_life}
  /coffee — Order the usual
  /focus \\<duration\\> — DND mode
  /tasks — Your todo list
  /remind \\<text\\> — Set a reminder

{bold_meta}
  /settings — Preferences
  /help — This menu

{italic_tip}

{separator}
""".strip()


@harvey_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — Donna introduces herself."""
    text = WELCOME_TEXT.format(
        bold_donna=md2_bold("DONNA"),
        italic_tagline=md2_italic("I know what you need before you do."),
        italic_ready=md2_italic("What do you need?"),
        separator=md2_separator(),
    )
    await update.message.reply_text(
        text=text,
        parse_mode="MarkdownV2",
        reply_markup=briefing_keyboard(email_count=0, meeting_count=0),
    )


@harvey_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list all commands."""
    text = HELP_TEXT.format(
        bold_donna=md2_bold("DONNA"),
        bold_commands=md2_bold("COMMANDS"),
        bold_daily=md2_bold("Daily Intelligence"),
        bold_people=md2_bold("People & Search"),
        bold_eng=md2_bold("Engineering"),
        bold_life=md2_bold("Life"),
        bold_meta=md2_bold("Meta"),
        italic_tip=md2_italic("Tip: Just type naturally — I understand context."),
        separator=md2_separator(),
    )
    await update.message.reply_text(text=text, parse_mode="MarkdownV2")
```

- [ ] **Step 5: Implement bot application factory**

```python
# src/donna_bot/bot.py
"""Bot application factory — wires everything together."""

from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from donna_bot.config import Settings
from donna_bot.auth.token_manager import TokenManager
from donna_bot.graph.client import GraphClient
from donna_bot.handlers.start import start_command, help_command
from donna_bot.middleware.security import set_authorized_chat_id

logger = logging.getLogger(__name__)


def create_app() -> Application:
    """Build and configure the Donna Telegram bot application."""
    settings = Settings.from_env()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Auth
    token_mgr = TokenManager(
        app_id=settings.graph_app_id,
        tenant_id=settings.graph_tenant_id,
    )

    # Graph client
    graph = GraphClient(token_manager=token_mgr)

    # Security — only Harvey
    set_authorized_chat_id(settings.harvey_chat_id)

    # Build application
    app = Application.builder().token(settings.telegram_token).build()

    # Store shared resources in bot_data
    app.bot_data["settings"] = settings
    app.bot_data["token_mgr"] = token_mgr
    app.bot_data["graph"] = graph

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Donna is ready. Waiting for Harvey...")
    return app
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_handlers/test_start.py -v`
Expected: Passed

- [ ] **Step 7: Verify bot starts (manual check)**

Run: `python -m donna_bot`
Expected: "Donna is ready. Waiting for Harvey..." (will fail without .env — that's OK)

- [ ] **Step 8: Commit**

```bash
git add src/donna_bot/bot.py src/donna_bot/handlers/ src/donna_bot/state/
git commit -m "feat(bot): application shell — /start, /help, state machine, handler routing"
```

---

## VI. Phase 2 — The Briefing (Tasks 9-12)

### Task 9: Graph Domain Modules — /me, Presence

**Files:**
- Create: `src/donna_bot/graph/me.py`
- Test: `tests/test_graph/test_me.py`

Build the `/me` (profile) and `/me/presence` Graph calls. Extract Harvey's display name, email, job title, and current presence status. This powers the greeting and availability display.

- [ ] Write test: `test_get_profile` asserts displayName and mail from mock
- [ ] Write test: `test_get_presence` asserts availability from mock
- [ ] Implement `graph/me.py` with `get_profile()` and `get_presence()`
- [ ] Run tests, verify pass
- [ ] Commit: `feat(bot): graph /me + presence modules`

### Task 10: Graph Calendar Module

**Files:**
- Create: `src/donna_bot/graph/calendar.py`
- Test: `tests/test_graph/test_calendar.py`

Build calendar operations: today's meetings, week view, free/busy analysis. Uses `/me/calendarView` with start/end datetime params.

- [ ] Write test: `test_get_today_meetings` with mock calendarView response
- [ ] Write test: `test_get_week_meetings` with 7-day range
- [ ] Write test: `test_calc_focus_time` with overlapping meetings
- [ ] Implement `graph/calendar.py` with `get_today()`, `get_week()`, `calc_focus_time()`
- [ ] Run tests, verify pass
- [ ] Commit: `feat(bot): graph calendar module — today, week, focus time`

### Task 11: Graph Mail Module

**Files:**
- Create: `src/donna_bot/graph/mail.py`
- Test: `tests/test_graph/test_mail.py`

Build email operations: top unread, read single, reply, archive. Uses `/me/messages` with OData filters.

- [ ] Write test: `test_get_unread_top5` with mock messages response
- [ ] Write test: `test_get_email_by_id` with full message body
- [ ] Write test: `test_reply_to_email` with POST mock
- [ ] Implement `graph/mail.py` with `get_unread()`, `get_email()`, `reply()`, `archive()`
- [ ] Run tests, verify pass
- [ ] Commit: `feat(bot): graph mail module — inbox, read, reply, archive`

### Task 12: Morning Briefing Handler + Scheduled Job

**Files:**
- Create: `src/donna_bot/handlers/briefing.py`
- Create: `src/donna_bot/scheduler/__init__.py`
- Create: `src/donna_bot/scheduler/jobs.py`
- Test: `tests/test_handlers/test_briefing.py`

Wire everything together: `/brief` command fetches profile + calendar + emails, composes the briefing card, sends it with inline keyboard. JobQueue schedules it for 8:30 AM daily. Progress animation (edit message) while data loads.

- [ ] Write test: `test_brief_command_sends_briefing` with all mocks
- [ ] Write test: `test_briefing_shows_progress` verifying edit_message_text called
- [ ] Implement `handlers/briefing.py` — fetch graph data → progress → card → keyboard
- [ ] Implement `scheduler/jobs.py` — `schedule_morning_briefing()` using JobQueue
- [ ] Register handler and job in `bot.py`
- [ ] Run tests, verify pass
- [ ] Manual test: /brief in Telegram
- [ ] Commit: `feat(bot): morning briefing — graph integration, progress animation, scheduled job`

---

## VII. Phase 3 — Email Intelligence (Tasks 13-16)

### Task 13: Email List Handler with Inline Keyboards

**Files:** `src/donna_bot/handlers/email.py`

`/email` command shows top 10 unread emails with inline keyboard. Tapping an email transitions to EMAIL_READ state.

- [ ] Implement ConversationHandler entry → EMAIL_LIST state
- [ ] Show email list with format_email_list + email_list_keyboard
- [ ] Handle pagination ("more" button)
- [ ] Tests + commit

### Task 14: Email Read Handler

Callback from email list → shows full email with format_email_card + email_action_keyboard.

- [ ] Fetch full message body from Graph
- [ ] Display with smart truncation (first 2000 chars)
- [ ] Show attachments indicator
- [ ] Tests + commit

### Task 15: Email Compose/Reply Handler

"Reply" button → enters EMAIL_COMPOSE state. Harvey types text, Donna drafts in Harvey's voice (initially, just sends as-is; later, add style matching).

- [ ] ConversationHandler state for free-text input
- [ ] Confirm before sending (confirm_keyboard)
- [ ] Call Graph `POST /me/messages/{id}/reply`
- [ ] Tests + commit

### Task 16: Full Email Conversation Flow

Wire Tasks 13-15 into a ConversationHandler with proper state transitions: EMAIL_LIST ↔ EMAIL_READ ↔ EMAIL_COMPOSE ↔ IDLE.

- [ ] Build ConversationHandler with all states
- [ ] Register in bot.py
- [ ] Integration test: full flow from /email → read → reply → back
- [ ] Commit

---

## VIII. Phase 4 — Calendar & People Intelligence (Tasks 17-20)

### Task 17: Calendar Day/Week Handler

`/cal` shows today's meetings → tap for detail → week view option.

### Task 18: Meeting Prep Handler

5 minutes before each meeting, auto-send prep card with context and talking points. Uses JobQueue to schedule per-meeting jobs.

### Task 19: People Lookup Handler

`/who <name>` searches People API → shows person card with org chart, availability, recent interactions.

### Task 20: Org Chart Navigation

From person card, "Org Chart" button shows manager → reports chain.

---

## IX. Phase 5 — Search & Engineering (Tasks 21-24)

### Task 21: M365 Cross-Tenant Search

`/search <query>` calls POST `/search/query` across emails, files, Teams messages, events. Shows results grouped by type with inline keyboards.

### Task 22: Natural Language Fallback

Messages that don't match any command → intent detection → route to appropriate handler. "Check my emails" → EMAIL_LIST. "Who owns auth service?" → PEOPLE_SEARCH.

### Task 23: PR Intelligence (GitHub API)

`/pr` shows open PRs from GitHub. Uses GitHub MCP server or direct API.

### Task 24: Build/Deploy Watchdog

Monitor pipeline status. Alert on failures.

---

## X. Phase 6 — Proactive Intelligence (Tasks 25-27)

### Task 25: Meeting Prep Auto-Scheduler

On bot start, scan today's calendar and schedule prep-card jobs for each meeting (meeting time - 5 min).

### Task 26: End-of-Day Summary

6:30 PM job: summarize what Harvey accomplished today — PRs merged, emails sent, meetings attended.

### Task 27: Pattern Detection

Detect patterns: "It's 9 AM and Harvey hasn't ordered coffee yet" → suggest. "12 hours online" → nudge to go home.

---

## XI. Phase 7 — Life & Extras (Tasks 28-30)

### Task 28: Food Ordering (Coffee)

`/coffee` → Donna orders the usual (VCB from Kink). Uses Swiggy MCP tools if available, otherwise stores preference and reminds.

### Task 29: Focus Mode

`/focus 2h` → set Teams presence to DND, queue non-critical notifications, auto-resume after duration.

### Task 30: Tasks & Reminders

`/tasks` → manage personal todo list. `/remind <text> at <time>` → schedule reminder message.

---

## XII. Phase 8 — Telegram Mini App Dashboard (Future)

Build a web-based dashboard that opens inside Telegram as a Mini App:
- Full morning briefing with interactive charts
- Sprint board (kanban)
- Calendar heat map
- Email inbox with swipe actions

This uses Telegram's WebApp API to embed HTML/JS inside the bot conversation. Served locally via the bot's HTTP server.

---

## XIII. Scenario Coverage Matrix

Every scenario from CAPABILITIES.md mapped to which handler covers it:

| Scenario | Handler | State | Phase |
|----------|---------|-------|-------|
| Morning briefing | briefing.py | BRIEFING | 2 |
| Coffee order | food.py | FOOD_ORDER | 7 |
| Standup prep | briefing.py | BRIEFING | 2 |
| Email triage | email.py | EMAIL_LIST | 3 |
| Email reply | email.py | EMAIL_COMPOSE | 3 |
| Teams triage | search.py | SEARCH | 5 |
| Meeting prep | calendar.py | MEETING_PREP | 4 |
| Calendar view | calendar.py | CALENDAR_DAY | 4 |
| Focus time | focus.py | FOCUS | 7 |
| Who owns X | people.py | PEOPLE_SEARCH | 4 |
| Org chart | people.py | PEOPLE_DETAIL | 4 |
| PR review | pr.py | PR_LIST | 5 |
| PR nudge | pr.py | PR_DETAIL | 5 |
| Incident alert | incident.py | INCIDENT | 6 |
| Incident analysis | incident.py | INCIDENT_ANALYSIS | 6 |
| Build watchdog | pr.py | — (proactive) | 5 |
| Sprint status | briefing.py | BRIEFING | 2 |
| Task prioritization | tasks.py | TASKS | 7 |
| End of day summary | briefing.py | — (scheduled) | 6 |
| Reminders | tasks.py | REMINDER | 7 |
| M365 search | search.py | SEARCH | 5 |
| Debug partner | fallback.py | IDLE | 5 |
| Architecture advisor | fallback.py | IDLE | 5 |
| Spec intelligence | search.py | SEARCH | 5 |
| Wiki search | search.py | SEARCH | 5 |
| Natural language | fallback.py | IDLE | 5 |
| Wellbeing nudge | scheduler/jobs.py | — (proactive) | 6 |

---

## XIV. Error Handling Matrix

| Error | User Sees | Recovery |
|-------|-----------|----------|
| WAM auth fails (laptop locked) | "I need Harvey's laptop to access Graph. I'll retry in 5 minutes." | Auto-retry via scheduler |
| Graph 401 (token expired) | Nothing — silent refresh | TokenManager.ensure_token() |
| Graph 429 (throttled) | Nothing — silent retry | Client retry with Retry-After |
| Graph 500 (server error) | "Microsoft is having a moment. I'll try again shortly." | Retry with exponential backoff |
| Network timeout | "I lost connection. Retrying..." | Auto-retry 3x |
| Telegram API error | Log error, no user message | Internal logging |
| Unknown command | "I didn't catch that. Try /help for what I can do." | Route to fallback handler |
| Empty results | Context-specific: "No unread emails. Inbox zero!" | Positive framing |
| Permission denied (403) | "I don't have access to that. Harvey might need to grant permission." | Log + suggest fix |

---

## XV. Personality Layer

Donna isn't a generic bot. Her responses have character:

| Situation | Generic Bot | Donna |
|-----------|-------------|-------|
| No emails | "You have no unread emails." | "Inbox zero. Suspicious. Did someone else clear it?" |
| 12h online | (nothing) | "12 hours, Harvey. The build is green. Go home." |
| Coffee time | "Would you like to order coffee?" | "It's 9. VCB from Kink? Same as always." |
| Meeting in 5 | "You have a meeting in 5 minutes." | "1:1 with your manager in 5. I've pulled your sprint metrics. Go crush it." |
| Incident mitigated | "Incident resolved." | "Sev2 auto-mitigated at 2am. You slept through it. You're welcome." |
| Weekend login | (nothing) | "It's Saturday. Urgent or bored? Because if it's the latter, close the laptop." |
| First message of day | "Hello!" | "Morning, Harvey. Strong coffee kind of day — you have 6 meetings." |

---

**Plan complete and saved to `docs/plans/2026-04-23-donna-telegram-bot.md`.**
