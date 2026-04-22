# ADR-002: Copilot CLI as Donna's Brain

> **Status:** Accepted
> **Date:** 2026-04-22
> **Decision:** Use GitHub Copilot CLI as the AI reasoning engine

## Context

Donna needs an AI brain that can:
- Understand natural language commands
- Access enterprise tools (IcM, ADO, Kusto, GitHub)
- Execute multi-step workflows
- Maintain conversation context
- Extend capabilities via MCP servers

## Decision

**GitHub Copilot CLI** — invoked as a subprocess from Tauri's Rust backend.

### Reasons:
1. **MCP ecosystem** — already has IcM, ADO, Kusto, GitHub, Swiggy integrations
2. **Conversation context** — maintains session state across turns
3. **Tool calling** — native support for structured tool invocation
4. **Auth** — leverages existing GitHub/Microsoft auth
5. **Extensible** — new MCP servers = new capabilities, no code changes
6. **Already proven** — Donna's personality and capabilities are validated in CLI

### Architecture:
```
[Tauri Frontend] ←IPC→ [Rust Backend] ←subprocess→ [Copilot CLI]
                                         ↕
                                    [MCP Servers]
                                    ├── IcM
                                    ├── ADO
                                    ├── GitHub
                                    ├── Kusto
                                    ├── Swiggy
                                    └── Calendar (future)
```

### Trade-offs:
- Subprocess management adds complexity (process lifecycle, stdin/stdout parsing)
- Copilot CLI may have rate limits
- No streaming support initially (batch request/response)
- Dependent on Copilot CLI availability and updates

## Consequences

- Rust backend manages Copilot CLI process lifecycle
- IPC protocol: JSON messages over stdin/stdout
- MCP server configuration shared between CLI and Donna app
- Donna's personality defined in skill file, loaded by CLI
