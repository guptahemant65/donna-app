# ADR-003: Always-Alive Cloud Brain Architecture

> **Status:** Accepted  
> **Date:** 2026-04-23  
> **Decision:** Donna runs as a cloud brain (Azure Container Instance) + local body (Tauri) + phone line (Telegram Bot). She is alive 24/7, not just when the laptop is on.

## Context

Donna was initially designed as a desktop app — alive when the laptop is open, dead when it's closed. Harvey rejected this:

> *"I want you to be as living as I'm 24x7. Sending me texts on telegram when I'm not on laptop. Constantly trying to help Harvey in whatever way you can."*

This changes Donna from "an app" to "a living entity with multiple bodies."

## Options Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| **Desktop-only** | Tauri app, dies when laptop closes, catches up on resume | ❌ Not alive enough |
| **Desktop + daemon** | Tauri app + lightweight system tray service | ❌ Still dies when laptop shuts down |
| **Cloud brain + local body** | Azure Container Instance runs 24/7, Tauri syncs when online | ✅ Selected |
| **Adopt OpenClaw** | Use open-source agent framework (180K★, TypeScript) | ❌ Language mismatch, toy memory, no MS enterprise skills |
| **Pure cloud (Lindy-style)** | All cloud, no local presence | ❌ Loses Windows Local APIs, clipboard, active window context |

## Decision

**Three-layer architecture:**

1. **Cloud Brain** (Azure Container Instance, ~$5-10/month)
   - Always alive. Polls Graph, IcM, ADO, GitHub every 2-10 min.
   - Runs decision engine ("is this worth waking Harvey?")
   - PostgreSQL + pgvector for shared memory
   - Heartbeat scheduler for proactive tasks

2. **Local Body** (Tauri app)
   - Full Donna UI when laptop is open
   - Windows Local APIs (clipboard, active window, keystrokes)
   - Syncs with Cloud Brain on connect
   - Desktop signals NEVER leave the local machine

3. **Phone Line** (Telegram Bot)
   - Donna's way to reach Harvey anywhere
   - Morning briefings, incident alerts, actionable replies
   - Runs via Cloud Brain (always available)

## Why Not OpenClaw

OpenClaw (github.com/open-claw/openclaw) is the most impressive open-source agent framework available — 180K+ stars, 5K+ skills, MIT license, messaging-first design. We considered adopting it and decided against it:

1. **TypeScript vs Rust** — 450K lines of Node.js doesn't compose cleanly with Tauri's Rust backend
2. **Markdown memory vs cognitive architecture** — Our 4-tier memory (Working → Episodic → Semantic → Procedural) is categorically better
3. **Consumer skills vs enterprise skills** — WAM broker auth, IcM, Kusto, ADO don't exist in ClawHub
4. **Personality is architecture** — Donna's Five Laws and Depth Protocol are decision-making frameworks, not a system prompt overlay
5. **Governance risk** — Creator joined OpenAI (Feb 2026), project governance trajectory uncertain

**However:** OpenClaw's Gateway (message routing), Heartbeat (proactive scheduling), and messaging-first UX patterns are excellent and we adopt those concepts in our own implementation.

**Reference protocol:** When building new capabilities, check OpenClaw's skills directory for patterns and approaches. Learn from them, implement in our stack.

## Consequences

- Memory architecture moves from local-only SQLite to PostgreSQL + pgvector in Harvey's Azure subscription
- Need Azure Container Instance provisioning (estimated ~$5-10/month)
- Need Telegram Bot setup (BotFather, token management)
- Privacy model: everything runs on Harvey's Azure subscription, Harvey's Key Vault, no third-party SaaS
- Section IX (Memory) in CAPABILITIES.md needs reconciliation — currently says "all local," now partially cloud
