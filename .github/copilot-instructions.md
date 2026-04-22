# Donna App — Copilot Instructions

Donna: a proactive AI concierge Windows desktop app. Built with Tauri (Rust + web frontend), powered by Copilot CLI + MCP integrations.

## Tech Stack
- **Shell**: Tauri 2.0 (Rust backend + WebView2 frontend)
- **Frontend**: Vanilla HTML/CSS/JS (no frameworks — same as edog-studio)
- **Backend**: Rust (Tauri commands, subprocess management)
- **Brain**: GitHub Copilot CLI (subprocess, MCP routing)
- **Memory**: SQLite (structured) + Vector DB (semantic search)
- **Design**: F16 Standard (see hivemind/FEATURE_DEV_SOP.md)

## Non-Negotiable Rules
- Single-file HTML for mockups (Phantom standard)
- No frontend frameworks (vanilla JS only)
- Rust: clippy clean, no unwrap in production paths
- Git: conventional commits (`feat:`, `fix:`, `chore:`)
- UI: No emoji. Unicode symbols or inline SVG only.
- Before merge: `cargo clippy && cargo test && npm run build` — all must pass

## Context Loading Protocol
Load ONLY what your current task needs. Key docs:
- Feature specs: `docs/specs/features/F*/`
- Feature catalogue: `docs/specs/FEATURES.md`
- Architecture decisions: `docs/adr/`
- Development SOP: `hivemind/FEATURE_DEV_SOP.md`
- Design mockups: `docs/design/mocks/`
