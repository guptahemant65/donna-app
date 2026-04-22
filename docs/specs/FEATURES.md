# Donna — Feature Catalogue

> **Status:** Draft v1
> **Date:** 2026-04-22
> **Author:** Donna + Hemant Gupta

---

## Tier 1: Daily Drivers

Features used every single day. The core of Donna.

### F01 — Command Palette

**Priority:** P0 — Foundation
**Description:** Spotlight-style command palette summoned with `Alt+Space`. The primary interaction surface. Type to search, suggestions appear live, Enter to execute. Quick action chips for frequent operations. Always accessible, never in the way.

**Key behaviors:**
- Alt+Space to summon from anywhere (global hotkey, even when app is minimized to tray)
- Escape to dismiss
- Fuzzy search across all commands, recent items, and contextual suggestions
- Quick action chips: Coffee, Incidents, Builds, PRs, Schedule
- Persistent — command palette never leaves, contextual panels slide in alongside it

---

### F02 — Chat Mode

**Priority:** P0 — Foundation
**Description:** Full conversational interface with Donna. Expands from the command palette. Donna responds with personality — she's not a generic chatbot, she's Donna Paulsen. Typing indicator, staggered message animations, markdown rendering.

**Key behaviors:**
- Seamless transition from command palette to chat
- Message history preserved across sessions
- Donna's personality in every response (wit, sarcasm, anticipation)
- Rich content: code blocks, tables, links, status pills
- Context-aware — Donna knows what you're working on

---

### F03 — Morning Briefing

**Priority:** P0 — Daily use
**Description:** When you open the app (or on schedule), Donna gives you a 30-second digest of everything that happened overnight. No more checking 5 different tools.

**Covers:**
- Overnight IcM incidents (new, mitigated, resolved)
- PR comments and review requests
- Build failures on your branches
- Calendar: what's coming up today
- Anything Donna flagged as important while you were away

**Format:** Scannable cards, not a wall of text. Each item is actionable — click to drill in.

---

### F04 — Standup Prep

**Priority:** P0 — Daily use
**Description:** "Prep me for standup" — Donna pulls yesterday's commits, current sprint items, blockers, and formats them into a ready-to-read standup script.

**Sources:**
- Git log (last 24h, your commits)
- ADO work items (assigned to you, updated recently)
- Active blockers (incidents, blocked PRs, failed builds)
- Calendar conflicts

**Output:** Structured text you can read verbatim or paste into Teams.

---

### F05 — Contextual Panels

**Priority:** P0 — Foundation
**Description:** Panels slide in from the right when you need depth on a specific topic. They're not pages — they're summoned, used, and dismissed. Command palette stays visible on the left (~40% width).

**Panels:**
- **Incidents** — Active IcM incidents, severity badges, timeline, impact, TSG links, Kusto + Mitigate actions
- **Pull Requests** — "Needs Your Review" + "Your PRs", approval status, diff stats, merge conflict warnings
- **Sprint Dashboard** — Sprint progress bar, burndown mini-chart, work items with status pills, blocked items highlighted

**Behavior:**
- Spring animation slide-in (300ms)
- Glassmorphism backdrop
- Close with ✕ or Escape
- Activity bar on the left for quick switching between panels

---

### F06 — Notification Toasts

**Priority:** P1 — Important
**Description:** Proactive notifications that appear as toasts. Auto-dismiss with progress bars. Not annoying — Donna only surfaces what matters.

**Triggers:**
- IcM incident assigned to your team
- Build failure on your branch
- PR approved / changes requested
- Delivery tracking (coffee ETA)
- Calendar reminder (5 min before meeting)

**Rules:**
- Max 3 visible toasts at once
- Sev1 incidents never auto-dismiss — require acknowledgment
- Mute mode available (right-click tray → Mute)

---

### F07 — System Tray Presence

**Priority:** P0 — Foundation
**Description:** Donna lives in the system tray. Always on, never intrusive. Status dot indicates her state (green = all clear, amber = attention needed, red = incident active). Right-click for context menu.

**Tray menu:**
- Open Donna (Alt+Space)
- Preferences
- Mute notifications
- Quit

---

## Tier 2: Power Moves

Features used weekly. Make Donna indispensable for engineering workflows.

### F08 — Incident Commander

**Priority:** P1 — High impact
**Description:** When an IcM incident fires, Donna doesn't just notify — she takes action. Auto-pulls Kusto logs, runs TSG analysis, drafts the comms, suggests mitigation steps. You go from "what happened?" to "here's the fix" in under a minute.

**Workflow:**
1. IcM alert triggers → Donna intercepts
2. Auto-runs relevant Kusto queries against the regional cluster
3. Matches error patterns against TSG knowledge base
4. Drafts incident summary + suggested mitigation
5. Presents everything in the Incidents panel
6. One-click to post analysis to IcM discussion

**MCP integrations:** IcM MCP, Kusto MCP, ADO MCP

---

### F09 — PR Reviewer

**Priority:** P1 — High impact
**Description:** "Review PR #1234" — Donna reads the diff, understands the context, spots potential bugs, and drafts inline review comments. Not a linter — a reviewer who understands the codebase.

**Capabilities:**
- Full diff analysis with codebase context
- Bug detection (null checks, error handling, race conditions)
- Style consistency checks against repo conventions
- Draft review comments (you approve before posting)
- Summary comment with overall assessment

**MCP integrations:** GitHub MCP, ADO MCP

---

### F10 — Clipboard Intelligence

**Priority:** P1 — High impact
**Description:** Copy a stack trace → Donna intercepts it, auto-analyzes, identifies the error pattern, suggests the fix. Copy a Kusto query → Donna offers to run it. Copy a JSON blob → Donna pretty-prints and validates it.

**Triggers:**
- Stack trace detected → analyze + suggest fix
- Kusto query detected → offer to run against cluster
- JSON/XML detected → format + validate
- URL detected → preview + extract metadata
- Error code detected → look up in knowledge base

---

### F11 — Context Switching

**Priority:** P2 — Productivity
**Description:** "Switch to LiveTable" → Donna loads the right repo, ADO board, open PRs, active incidents, and recent files for that project. Zero manual setup when jumping between projects.

**Per-project context:**
- Default repo + branch
- ADO project + team + current sprint
- Active incidents filter
- Recent files and bookmarks
- Custom commands and shortcuts

---

### F12 — Meeting Prep

**Priority:** P2 — Productivity
**Description:** 5 minutes before a meeting, Donna surfaces the agenda, related work items, last meeting's action items, and any PRs/incidents the attendees might bring up.

**Sources:**
- Calendar (Teams/Outlook integration)
- ADO work items linked to meeting attendees
- Recent PRs from meeting attendees
- Active incidents involving attendees' teams

---

### F13 — Smart Scheduling

**Priority:** P2 — Productivity
**Description:** "Block 2 hours for deep work" → Donna checks your calendar, finds gaps, creates the block. "Find time with Alice and Bob" → Donna checks availability and proposes slots.

**Capabilities:**
- Calendar gap detection
- Focus time blocking with "Do Not Disturb" integration
- Multi-person availability check
- Recurring block creation

---

## Tier 3: The Dream

Features that make Donna feel truly sentient. Long-term vision.

### F14 — Persistent Memory

**Priority:** P1 — Foundational for intelligence
**Description:** Donna remembers every conversation, every preference, every pattern — across sessions. Not just chat history, but structured knowledge: "Hemant always uses Kink Coffee HSR", "PR reviews on LiveTable repo take priority", "standup is at 10:30 AM IST".

**Architecture:**
- Local SQLite for structured facts (preferences, patterns, contacts)
- Vector DB (embedded) for semantic search across conversation history
- Automatic fact extraction from conversations
- Privacy-first — all data local, never sent to cloud

---

### F15 — Proactive Alerts

**Priority:** P1 — High value
**Description:** Donna doesn't wait to be asked. She watches your pipelines, PRs, incidents — and taps your shoulder *before* you need to check.

**Proactive behaviors:**
- Build failed on your branch → notify immediately
- PR has been open >24h without review → nudge reviewers
- Sprint burndown off track → flag in morning briefing
- Incident mitigated → confirm and close the loop
- Coffee delivery arriving → "Your VCB is 5 minutes out"

---

### F16 — Voice Mode

**Priority:** P3 — Future
**Description:** Talk to Donna. Literally. Whisper a question while you're in a meeting. She listens, processes, and responds either with voice or text (your choice).

**Modes:**
- Push-to-talk (hotkey)
- Whisper mode (low-volume mic, processes speech)
- Response: voice (TTS) or text (in app)

---

### F17 — Team Pulse

**Priority:** P3 — Future
**Description:** "Who's free?" → Donna checks Teams presence, ongoing meetings, focus time blocks. "When can I reach Alice?" → checks her calendar and suggests best times.

**Capabilities:**
- Teams presence integration (Available/Busy/DND/Away)
- Calendar-aware availability
- Team workload visualization
- Best-time-to-reach suggestions

---

### F18 — Swiggy Integration

**Priority:** P2 — Quality of life
**Description:** "Get me coffee" — one command. Donna knows your address, your usual order, your coupon, the nearest store. Orders it, tracks it, tells you when it arrives. No questions asked.

**Standing orders:**
- Kink Coffee HSR → Vietnamese Cold Brew (VCB)
- Address: D-6-EAST, Trinity Acres and Woods, HSR Layout
- Coupon: PARTNERSHIP-COMMUNITIES
- Delivery note: "Only one ice cube. Extra strong."
- Payment: COD (until online payment API available)

**MCP integrations:** Swiggy Food MCP, Swiggy Instamart MCP

---

## Feature Index

| ID | Name | Tier | Priority | Status |
|----|------|------|----------|--------|
| F01 | Command Palette | 1 | P0 | Design |
| F02 | Chat Mode | 1 | P0 | Design |
| F03 | Morning Briefing | 1 | P0 | Concept |
| F04 | Standup Prep | 1 | P0 | Concept |
| F05 | Contextual Panels | 1 | P0 | Design |
| F06 | Notification Toasts | 1 | P1 | Design |
| F07 | System Tray Presence | 1 | P0 | Design |
| F08 | Incident Commander | 2 | P1 | Concept |
| F09 | PR Reviewer | 2 | P1 | Concept |
| F10 | Clipboard Intelligence | 2 | P1 | Concept |
| F11 | Context Switching | 2 | P2 | Concept |
| F12 | Meeting Prep | 2 | P2 | Concept |
| F13 | Smart Scheduling | 2 | P2 | Concept |
| F14 | Persistent Memory | 3 | P1 | Concept |
| F15 | Proactive Alerts | 3 | P1 | Concept |
| F16 | Voice Mode | 3 | P3 | Future |
| F17 | Team Pulse | 3 | P3 | Future |
| F18 | Swiggy Integration | 3 | P2 | Design |
