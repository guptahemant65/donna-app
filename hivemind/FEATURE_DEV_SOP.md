# Donna — Feature Development SOP

> **Status:** ACTIVE
> **Established:** 2026-04-22
> **Based on:** EDOG Studio F16 Standard
> **Rule:** Follow this for every feature. No shortcuts.

---

## The Principle

**Divide until trivial. Research before designing. Design before building. Verify before shipping.**

---

## Phase 0: Foundation Research

**Goal:** Understand what exists before imagining what to build.

| Task | What | Output |
|------|------|--------|
| P0.1 | **Existing capability audit** — what can Copilot CLI + MCP already do? What gaps exist? | `research/p0-foundation.md` §1 |
| P0.2 | **Integration mapping** — which MCP servers are needed? What APIs? Auth flows? | `research/p0-foundation.md` §2 |
| P0.3 | **Industry research** — how do the best tools solve this? Raycast, Linear, Arc, Warp, Fig. | `research/p0-foundation.md` §3 |

**Gate:** P0 must be DONE before P1 starts.

---

## Phase 1: Component Deep Specs

**Goal:** Define every scenario, every edge case, every interaction — grounded in P0 research.

| Task | What | Output |
|------|------|--------|
| P1.N | **One spec per component** — independent, complete, verifiable | `components/C0N-name.md` |

**Per scenario:**
1. Name + one-liner
2. Detailed description
3. Technical mechanism
4. MCP/API integration points
5. Edge cases
6. Error recovery
7. Priority (P0/P1/P2)

**Gate:** All component specs DONE before P2 starts.

---

## Phase 2: Architecture

**Goal:** A senior engineer can implement from the spec without asking questions.

| Task | What | Output |
|------|------|--------|
| P2.1 | **Data model** — Tauri commands, TypeScript interfaces, SQLite schemas | `architecture.md` §1 |
| P2.2 | **Core engine** — Copilot CLI invocation, MCP routing, memory layer | `architecture.md` §2 |
| P2.3 | **Storage** — SQLite schema, vector DB, preferences | `architecture.md` §3 |
| P2.4 | **IPC** — Tauri command↔frontend protocol | `architecture.md` §4 |

**Gate:** Architecture DONE before P3 starts.

---

## Phase 3: Design

**Goal:** Every pixel defined before code.

| Task | What | Output |
|------|------|--------|
| P3.1 | **Interactive mockup** — Phantom-built, fully functional HTML prototype | `mocks/feature-name.html` |
| P3.2 | **State matrix** — every state, transition, edge case | `states/component-name.md` |

**Gate:** Mockup approved + state matrix complete before P4 starts.

---

## Phase 4: Implementation

**Goal:** Build exactly what was designed. One component per agent.

**Rules:**
- One agent per component (parallel dispatch OK)
- Each agent reads ALL specs as context
- Tests written BEFORE implementation (TDD)
- Every interaction from the mockup must work identically

**Gate:** All components built + integrated before P5 starts.

---

## Phase 5: Quality Gates

**Goal:** Zero preventable defects.

| Gate | Check |
|------|-------|
| G1 | Build passes (`cargo build` + `npm run build`) |
| G2 | All tests pass |
| G3 | Every scenario from state matrix verified |
| G4 | Performance targets met (startup <2s, palette <50ms, panel <200ms) |
| G5 | Edge cases handled (offline, timeout, auth expired, empty state) |
| G6 | Accessibility (keyboard nav, screen reader, contrast) |
| G7 | Dogfood — use it for a real workflow before shipping |

**Gate:** ALL gates pass before merge.

---

## The F16 Standard

Every UI element in Donna follows the F16 Standard:

1. **Layered Token Architecture** — semantic surfaces, borders, text, accent, elevation
2. **Physics-Based Motion** — spring overshoot, three curves, three speeds
3. **Purposeful Animation** — 25+ named keyframes per complex feature
4. **Hover That Teaches** — every interactive element reveals affordance
5. **Typography Precision** — Inter + JetBrains Mono, 6-stop scale
6. **Compound Elevation** — dual shadows at every level
7. **Accent Restraint** — accent is a scalpel, not a paintbrush
8. **Context Saturation** — hunt for context, search for inspiration, then create
