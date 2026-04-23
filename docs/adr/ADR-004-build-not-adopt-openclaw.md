# ADR-004: Build Our Own Agent, Learn from OpenClaw

> **Status:** Accepted  
> **Date:** 2026-04-23  
> **Decision:** Build Donna's agent runtime in Rust + Python. Do not adopt OpenClaw or any existing agent framework. Use OpenClaw as a reference and inspiration.

## Context

OpenClaw (formerly Clawdbot, by Peter Steinberger) is the dominant open-source AI agent framework in 2026:
- 180K+ GitHub stars, MIT license
- 450K lines of TypeScript, 5,000+ community skills
- Architecture: Gateway → Brain → Memory → Skills → Heartbeat
- Messaging-first: Telegram, WhatsApp, Discord, Slack, iMessage
- Local-first with persistent memory
- Model-agnostic (Claude, GPT, DeepSeek, Ollama)

The question: should Donna adopt OpenClaw as her runtime, or build her own?

## Decision

**Build our own. Use OpenClaw as a reference library.**

### What We Build

| Component | Technology | OpenClaw Equivalent |
|-----------|-----------|-------------------|
| Gateway | Python (`python-telegram-bot`) + Rust IPC | Gateway module (TypeScript, multi-channel) |
| Brain | LLM via Copilot CLI + MCP | Brain module (LLM orchestration) |
| Memory | SQLite + ChromaDB/LanceDB + custom graph → PostgreSQL + pgvector (cloud) | Memory module (Markdown files) |
| Skills | MCP servers (Graph, IcM, ADO, Kusto, GitHub...) | Skills module (ClawHub plugins) |
| Heartbeat | APScheduler in Cloud Brain daemon | Heartbeat module (cron-like scheduler) |
| UI | Tauri 2.0 (Rust + WebView2) | N/A (OpenClaw is headless/messaging-only) |

### What We Steal (Ideas Only)

1. **Gateway pattern** — Single interface routing to multiple messaging channels. Start with Telegram, design for expansion.
2. **Heartbeat pattern** — Background scheduler that is context-aware, not just cron. Can evaluate whether a scheduled task is still relevant before executing.
3. **Messaging-first UX** — Interact with the agent as naturally as texting a coworker. No special syntax, no forms.
4. **Skills as hot-swappable modules** — Each capability is isolated, independently deployable, can be enabled/disabled.
5. **Local-first memory ownership** — User owns all data. Nothing leaves without explicit permission.

### Why We Don't Adopt

| Factor | OpenClaw | Donna | Gap |
|--------|----------|-------|-----|
| Language | TypeScript (Node.js) | Rust + Python | Two runtimes is a hostage situation |
| Memory | Markdown files | 4-tier cognitive architecture with vector search + knowledge graph | Categorically different capability |
| Skills | 5,000 consumer skills (weather, smart home) | 11 enterprise skills (WAM auth, Graph, IcM, Kusto, ADO) | Zero overlap |
| Identity | Generic agent framework | Donna — specific personality, specific user, specific decision framework | Personality is architecture, not a prompt |
| Governance | MIT, but creator joined OpenAI Feb 2026 | We own it entirely | Full control |

## Consequences

- We accept the cost of building our own agent runtime (~1 week to MVP)
- We gain complete ownership of every layer
- We maintain OpenClaw as a reference: when building a new feature, check if they solved a similar problem
- We may contribute back if we solve problems they haven't (e.g., enterprise skills, cognitive memory)
