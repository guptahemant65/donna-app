# ADR-001: Tauri as Application Framework

> **Status:** Accepted
> **Date:** 2026-04-22
> **Decision:** Use Tauri 2.0 for the Donna desktop app

## Context

Donna needs a native Windows desktop application that:
- Runs as a system tray app with global hotkey support (Alt+Space)
- Renders a web-based UI (command palette, panels, chat)
- Invokes Copilot CLI and MCP servers from the backend
- Has a tiny footprint (~5MB binary)
- Starts instantly (<2s cold start)

## Options Considered

| Option | Binary Size | Memory | Native API | Web UI | Verdict |
|--------|------------|--------|-----------|--------|---------|
| **Tauri 2.0** | ~5MB | ~30MB | Rust FFI | WebView2 | ✅ Selected |
| Electron | ~150MB | ~200MB | Node.js | Chromium | Too heavy |
| .NET MAUI | ~20MB | ~80MB | C# | WebView2 | Overkill |
| Flutter | ~15MB | ~60MB | Dart FFI | Skia | Non-standard UI |

## Decision

**Tauri 2.0** — Rust backend + web frontend via WebView2.

### Reasons:
1. **Tiny binary** — 5MB vs Electron's 150MB. Donna should feel lightweight.
2. **System tray + global hotkey** — first-class support in Tauri 2.0
3. **Rust backend** — safe process management for Copilot CLI subprocess + MCP routing
4. **Web frontend** — reuse Phantom's HTML/CSS/JS design language directly
5. **WebView2** — ships with Windows 11, no bundled browser needed
6. **IPC** — Tauri's command system is clean and type-safe

### Trade-offs:
- Rust has a steeper learning curve than Node.js
- WebView2 behavior may differ slightly from Chromium (test thoroughly)
- Smaller ecosystem than Electron for desktop plugins

## Consequences

- Frontend code is vanilla HTML/CSS/JS (consistent with edog-studio approach)
- Backend is Rust (Tauri commands)
- Copilot CLI invoked as subprocess from Rust
- MCP servers accessed via HTTP from Rust backend
- All UI follows the F16 Standard design language
