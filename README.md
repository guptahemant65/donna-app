# Donna

> *"I don't get coffee. I anticipate when you'll need it, order your usual from the nearest Kink, apply your coupon, and have it waiting before you even think about caffeine."*

**Donna** is a proactive AI concierge — an always-on Windows desktop app that doesn't wait to be asked. She watches your pipelines, reviews your PRs, tracks your incidents, manages your calendar, and orders your coffee. All from a single command palette you summon with `Alt+Space`.

## Architecture

- **Shell**: Tauri (Rust backend + web frontend, ~5MB binary)
- **Brain**: GitHub Copilot CLI + MCP integrations
- **Memory**: Local SQLite + vector embeddings for persistent context
- **UI**: Command palette / Spotlight-style — summon with Alt+Space, dismiss with Escape

## Status

🚧 **Design Phase** — Feature catalogue defined, interactive mockup built, architecture in progress.

## Quick Links

- [Feature Catalogue](docs/specs/FEATURES.md)
- [Interactive Mockup](docs/design/mocks/donna-app-mockup.html)
- [Architecture Decision Records](docs/adr/)
- [Development SOP](hivemind/FEATURE_DEV_SOP.md)
