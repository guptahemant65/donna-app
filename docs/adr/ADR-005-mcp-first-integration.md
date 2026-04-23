# ADR-005: MCP-First Integration Architecture

**Status:** Accepted
**Date:** 2026-04-23
**Decision makers:** Harvey, Donna

## Context

We mapped 29 integrations in our capability spec and proved 32/44 Graph endpoints work via WAM broker auth (Graph probe POC). Meanwhile, the MCP ecosystem exploded:

- **Azure MCP Server** — 55 tools across 47+ Azure services (Kusto, Monitor, AppInsights, KeyVault, Cosmos, PostgreSQL, Redis, Storage, SignalR, and more). Ships built into VS 2026.
- **Azure DevOps MCP** — Remote server at `mcp.dev.azure.com/{org}`. Work items, PRs, pipelines, boards. Entra ID auth. Public preview.
- **IcM MCP Server** — 23+ tools. Incidents, on-call, customer impact, summaries. Already wired into Harvey's Copilot CLI.
- **Fabric MCP Server** — `Fabric.Mcp.Server` in the official `microsoft/mcp` catalog. Harvey's own product.
- **M365 MCP (Softeria)** — Open source, 171 Graph endpoints via MCP. Mail (13), Calendar (19), Teams (28), Files (20), OneNote (7), Planner (6), To-Do (5), SharePoint (12), Contacts, People, Presence, Search, Groups, Places, Online Meetings.
- **Work IQ MCP (Microsoft)** — Official 1st-party preview. Mail, Calendar, Teams, Presence. Governed via M365 Admin Center.
- **GitHub MCP** — Official. All repo, PR, issue, actions operations.
- **Playwright MCP** — Browser automation.
- **Stack Overflow Teams MCP** — Internal knowledge.
- **External MCPs** — Slack (official), Gmail (Google), Google Calendar (Google), Notion, Spotify.

The question: should Donna use MCP servers as her primary integration layer, or continue with direct API calls?

## Decision

**MCP-first with direct API fallback.**

### Primary Layer: MCP Servers

Use MCP for all integrations where an MCP server exists. Benefits:
- Standard protocol — any LLM can discover and use tools dynamically
- Session state, tool discovery, schema validation built in
- Hours to integrate vs weeks of custom API code
- Community maintained, continuously updated

### Fallback Layer: Direct API (WAM Broker + REST)

Use direct Graph API calls for:
1. **Endpoints MCP doesn't cover** (~10 of our 32 proven endpoints): insights/used, insights/shared, organization, transitiveMemberOf, outlook/masterCategories, settings, notifications, beta/profile
2. **Performance-critical paths** — incident response polling, real-time loops where 5ms vs 20ms matters
3. **Beta endpoints** — MCP servers typically only cover GA endpoints
4. **Windows Local APIs** — no MCP exists, pure Tauri/Win32/COM

### Coverage Analysis

Our 32 proven Graph endpoints:
- **22 (69%)** — covered by M365 MCP, use MCP
- **10 (31%)** — not in MCP, use direct API fallback

M365 MCP provides **~80 additional endpoints** we never probed, including:
- `/me/findMeetingTimes` — find optimal meeting slots
- `/me/sendMail` — direct send (not just draft)
- `/me/mailboxSettings` — OOO, auto-reply, signatures
- `/places/*` — room booking (5 endpoints)
- `/me/onlineMeetings/*` — meetings, attendance, transcripts (11 endpoints)
- `/groups/*` — group management (11 endpoints)
- `/users/*` — cross-user lookup (11 endpoints)
- `/me/events/{id}/accept|decline|cancel` — respond to invites

### Performance Trade-off

| Metric | Direct REST | MCP |
|--------|------------|-----|
| Local latency | 1-10ms | 5-20ms (Python) |
| First call | ~instant | +80-150ms (session) |
| Overhead | 1x | 1.5-4x |
| Throughput | 2500+ req/s | 300 req/s (Python) |

For a personal assistant, the ~15ms overhead is imperceptible. We only go direct for sub-10ms polling loops.

## The Complete MCP Power Grid

### Tier 0 — Platform (Harvey's cloud infrastructure)
| Server | Tools | Auth | What Donna Gets |
|--------|-------|------|-----------------|
| Azure MCP (`aka.ms/azmcp`) | 55 | Azure CLI/MI | Kusto NL→KQL, Monitor, AppInsights, KeyVault, Cosmos, PostgreSQL, Redis, Storage, SignalR, compute, pricing, advisor, policy, resource health |

### Tier 1 — Microsoft Internal (Engineering superpowers)
| Server | Tools | Auth | What Donna Gets |
|--------|-------|------|-----------------|
| M365 MCP (Softeria) | 171 | OAuth/MSAL | Mail, Calendar, Teams, Files, Tasks, Planner, OneNote, SharePoint, People, Presence, Search, Groups, Places, Meetings |
| Azure DevOps MCP | ~40 | Entra ID | Work items, PRs, pipelines, boards, repos, branches, wikis |
| IcM MCP | 23 | Azure CLI | Incidents, on-call, customer impact, summaries, mitigation |
| Fabric MCP | TBD | Entra ID | LiveTable, Lakehouse, real-time analytics — Harvey's own product |
| GitHub MCP | ~30 | OAuth | Repos, PRs, issues, code search, commits, actions, workflows |
| Geneva / Jarvis MCP | TBD | Azure CLI/MI | Metrics (MDM), health/alerts, logs. Server exists: `AIOps-Evaluator-Agentic-Platform` PR #14508805. Alternative: Grafana MCP with Geneva datasource backend. DRI-grade telemetry. |
| Ev2 MCP | TBD | Entra ID | Deployment rollouts, rollout logs, failure investigation. Ev2 team confirmed "one in the works." Community version already built for DRI copilot use. |
| SCOPE MCP | ~5 | Local | Cosmos/SCOPE script validation (`scope_compile`). Exists: `gim-home/scopemcpserver` on GitHub. |

### Tier 1.5 — Confirmed / Coming Soon
| Server | Status | What Donna Gets |
|--------|--------|-----------------|
| PowerBI MCP | ✅ Live | NL queries over Power BI semantic models. Remote endpoint: `api.fabric.microsoft.com/v1/mcp/powerbi`. Docs + guides found in SharePoint. |
| Modeling MCP | ✅ Live | Fabric Modeling operations. Published by Microsoft Fabric Security team. |
| Fabric RTI MCP (`microsoft/fabric-rti-mcp`) | ✅ Live | Eventhouse, Azure Data Explorer (ADX), real-time analytics. GitHub open source. Actively used by FMLV, S360/Breeze teams. |
| Kusto AI Chat MCP | ✅ Live | KQL chat bot via custom MCP. Presentation by Jonathan Saraco. |
| Nitro V2 MCP | In development | Data pipeline management. Nitro team confirmed: "We are working on MCP servers for Nitro V2." |
| Work IQ MCP (Microsoft 1P) | Preview | Official M365 MCP — mail, calendar, Teams, presence. Admin-governed. Will replace Softeria when GA. |
| Azure SRE Agent MCP | Available | Uses MDM metrics via MCP. Same telemetry the on-call SRE agents use. Docs: `eng.ms/docs/.../sre-agent/.../usemdmmetrics` |
| DGrep MCP | Wanted | Geneva log search. DGrep SDK exists for programmatic search. Requested on Stack Internal Q480901. |

### Discovery: 1ES MCP Registry (`aka.ms/1mcp`)

The **1ES team** is building a standardized registry for all 1P MCP servers across Microsoft. This is the official catalog — one place to discover every internal MCP as product teams publish them. Jasmine Wang (1ES) is leading the effort to standardize MCP publishing and consumption.

**Key policy:** "DO NOT build an MCP Server to access resources whose API is owned by another Microsoft team unless the owning team explicitly grants permission." This means product teams are building their OWN MCPs — the ecosystem will keep growing organically.

**Source:** Stack Internal research (Q457808, Q462388, Q467657, Q471080) + M365 `/search/query` mining (3 waves, 17 queries).

### Agent Platforms Discovered (via M365 Search)

| Platform | Creator | What | Donna Relevance |
|----------|---------|------|-----------------|
| Daemon Foundry | Akshat Bordia | Command Copilot CLI agents from Teams threads. Live progress updates, directory browser. | Remote trigger for Donna — command her from Teams |
| Agency Cowork | Yang You, Nikhil Kaul | AI agent framework, multi-agent orchestration. `ahsi-microsoft/agency-cowork`. | Architecture reference for Donna's agent model |
| Agency Session Manager | Kunal Babre, Imran Siddique | Unified platform to discover, start, compose AI agents. | Session management patterns |
| Scout | Harsha Nagulapalli | AI ICM investigation partner. Kusto MCP + IcM MCP. Persona system. | Template for Donna's DRI mode |
| copilot-toolkit | Karlen Lie | Reusable skills & agents — generate-design-doc, pr-review, etc. | Skill library reference |

### Research Tools — Discovery Engine

Donna maintains awareness of new MCPs via two internal research tools:

1. **Stack Overflow Teams search** — keyword search across internal Q&A. Found Geneva, Ev2, SCOPE, Nitro MCPs, 1ES registry, WAM guidance.
2. **Microsoft Graph `/search/query`** — POST endpoint searching Harvey's entire M365 tenant (emails, files, Teams, events). POC: `poc/graph_search.py` (WAM broker auth).
   - "MCP server": 106 emails, 39,610 files, 1,209 Teams messages
   - Found: PowerBI MCP, Modeling MCP, Fabric RTI MCP, Kusto AI Chat MCP, Daemon Foundry, Agency Cowork, Scout, copilot-toolkit
   - Key contacts identified for follow-up: Akshat Bordia, Yang You, Harsha Nagulapalli, Karlen Lie, Jonathan Saraco

### Tier 2 — Ecosystem (Productivity & communication)
| Server | Tools | Auth | What Donna Gets |
|--------|-------|------|-----------------|
| Playwright MCP | ~15 | Local | Browser automation — anything without an API |
| Stack Overflow Teams MCP | ~10 | Auth | Internal knowledge search, Q&A, articles — also Donna's internal research tool |
| Slack MCP (official) | ~20 | OAuth | Slack messages, channels, DMs, reactions |
| Gmail MCP (Google) | ~15 | OAuth | Personal email management |
| Google Calendar MCP | ~10 | OAuth | Personal calendar (if Harvey uses GCal too) |

### Tier 3 — Direct API Only (No MCP exists)
| Integration | Protocol | Why Direct |
|-------------|----------|-----------|
| Windows Local APIs | Tauri/Win32/COM | Desktop signals — no MCP possible |
| Graph fallback endpoints | WAM + REST | 10 endpoints MCP doesn't cover |
| LinkedIn API | OAuth2 REST | No MCP server exists yet |
| Travel APIs | REST | No standard MCP server |
| Weather API | REST | Trivial, MCP overhead not worth it |
| Spotify API | OAuth2 REST | Community MCP exists but fragile |

## Consequences

### Positive
- Integration count explodes from 29 custom APIs to **25+ MCP servers + ~10 direct APIs** covering MORE surface area
- Time to integrate drops from weeks per integration to hours
- LLM can dynamically discover available tools — no hardcoded mapping
- Community AND product teams maintain MCP servers — we inherit updates for free
- Graph probe POC isn't wasted — it becomes the fallback layer
- Azure MCP Server alone gives us 55 cloud management tools we never planned for
- Geneva MCP gives DRI-grade telemetry — metrics, health, logs — without custom integration
- 1ES MCP Registry (`aka.ms/1mcp`) means new MCPs appear automatically as teams publish them
- Stack Internal + Graph `/search/query` proved invaluable as research tools — Donna uses them for ongoing discovery
- PowerBI MCP (`api.fabric.microsoft.com/v1/mcp/powerbi`) is live and gives NL querying over semantic models — no setup
- Daemon Foundry pattern shows how to command Donna from Teams — ready-made remote trigger architecture
- 5 agent platform discoveries provide architecture references for Donna's multi-agent model

### Negative
- Dependency on third-party MCP servers (Softeria is community, not Microsoft)
- MCP protocol overhead (~2-4x per call, but imperceptible for our use case)
- WAM broker auth issue still applies — MCP servers need the same corp tokens
- Work IQ MCP (Microsoft 1st-party) is still preview — may change
- Need to handle MCP server unavailability gracefully

### Risks
- Softeria M365 MCP could be abandoned (mitigated: it's open source, we can fork)
- MCP protocol could fragment (mitigated: Anthropic + Microsoft + Google all backing it)
- Auth flow still blocked for some endpoints regardless of layer (admin policy)
