# Donna — Design Brief for UI Summit

## What is Donna?

A personal AI concierge for a senior Microsoft engineer. A standalone Windows desktop app (Tauri 2.0 shell) powered by Copilot CLI. Think: Jarvis for your workday — knows your PRs, incidents, sprint, calendar, coffee order. Always-on, always anticipating.

**Named after Donna Paulsen** from Suits — the executive assistant who runs the show with confidence, precision, and personality.

## The Problem

Six design iterations. Six rejections. The user described what they want as **"a brand new next level minimalistic windows app."** We haven't found it.

## What Was Tried (and Why It Failed)

| Version | Direction | Fonts | Palette | Layout | Verdict |
|---------|-----------|-------|---------|--------|---------|
| v1-v2 | Dev-tool / glassmorphism | Inter, system | Purple accent, dark | Card-based dashboard | "still mid" |
| v3 | Warm glassmorphism | Inter, system | Warm palette, blur | Card grid | "still mid", "Phantom is the wrong guy" |
| v4 | Editorial / luxury | DM Serif Display, Plus Jakarta Sans | Espresso brown, cream | Two-panel dashboard | "is this what looks best to you?" (skeptical) |
| v5 | Newspaper / editorial deeper | Cormorant Garamond, Source Sans 3 | Charcoal + champagne gold | Two-column newspaper | "this looks more shitty" |
| v6 | Raycast / command palette | System fonts (Segoe UI Variable) | Cool zinc, indigo accent | Tab-based compact window | "this is also very bad" |

### The Pattern of Failure

Every version shares the same fundamental problem: **it looks like AI generated it.** Specifically:

1. **Flat visual hierarchy** — information is laid out but nothing guides the eye
2. **Generic structure** — header/content/footer or sidebar/main feels templated
3. **No spatial intelligence** — spacing is uniform rather than rhythmic
4. **Typography as decoration** — fonts are chosen to "look good" rather than to create hierarchy and flow
5. **Content as placeholder** — the data feels fake, which makes the whole design feel fake
6. **No personality** — despite being named after a character dripping with personality, every version is sterile

## What We Know About the User's Taste

- Microsoft engineer → lives in Windows 11, VS Code, Terminal daily
- Chose Tauri 2.0 (not Electron) → values native feel, performance, precision
- Said "minimalistic" multiple times → less is more, but "less" must be BETTER
- Rejected warm/editorial → doesn't want a lifestyle magazine
- Rejected dev-tool aesthetic → doesn't want another VS Code panel
- Rejected Raycast-style compact → maybe the window IS too small?
- **Has not named a reference app they love** — this is a critical gap

## Constraints

- **Platform**: Windows desktop app (Tauri 2.0 = Rust backend + WebView2 frontend)
- **Tech**: HTML/CSS/JS rendered in WebView2 (Chromium). No React/Vue.
- **Architecture**: Command palette IS the navigation (ADR decision, locked)
- **Views needed**: Morning brief, Chat/conversation, Sprint board, PR list, Incident dashboard
- **Character**: Should feel like talking to a confident, capable person — not using a tool
- **Typography**: Must work on Windows (Segoe UI Variable available, or custom web fonts)
- **No emoji**: Unicode symbols (●, ▸, ◆, ✕) or inline SVG only

## Open Questions for the Summit

1. **What does "minimalistic" mean here?** Is it Apple-minimal (whitespace as design element), Linear-minimal (dense but clean), or something else entirely?
2. **Dark or light?** Every version defaulted to dark. Has anyone tried light mode?
3. **Window metaphor**: Full-screen app? Floating panel? Always-on-top overlay? Sidebar dock?
4. **How much personality?** Should Donna feel like a person (conversational, warm) or a tool (precise, mechanical)?
5. **Reference apps**: What does the user reach for when they think "beautiful software"?
6. **Information density**: Engineer-dense (terminal, spreadsheet) or consumer-sparse (Apple, Arc)?

## Assets

- Repo: `guptahemant65/donna-app` (GitHub)
- Feature spec: `docs/specs/FEATURES.md` — 18 features catalogued
- All 6 mockups: `docs/design/mocks/` (only latest committed, but history available)
- Architecture: `docs/adr/ADR-001-tauri-framework.md`, `docs/adr/ADR-002-copilot-cli-brain.md`

## What We Need From This Summit

1. A **design direction** — not another mockup, but a clear aesthetic framework (palette logic, type scale, spatial system, interaction model)
2. A **reference board** — 3-5 apps/interfaces that represent the target quality bar
3. A **first-principles layout** — how information should flow, not just where boxes go
4. Answer to: **"If Donna Paulsen were software, what would she look like?"**
