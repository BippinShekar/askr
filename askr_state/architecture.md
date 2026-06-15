# Architecture

*Auto-generated at checkpoint — 2026-06-15 16:42 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages session lifecycle and state transitions

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Interfaces with `./askr_state/` for state storage

**Client Handlers** (`./askr/clients/`)
- Multi-client support (IDE, CLI, external integrations)
- Abstracts communication protocols

**IDE Integration** (`./askr/ide/`)
- IDE-specific adapters and protocol handlers
- Bridges between Askr core and editor environments

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Alerts for session state changes and completions

**Hooks** (`./askr/hooks/`)
- Pre/post-execution lifecycle hooks
- Integration points for custom behaviors

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Session state persistence layer (file-based or database)
- **`./.llm_snapshot/`** — LLM interaction snapshots and context caching
- **`./.claude/`** — Claude-specific configuration and artifacts

## External Integrations
- **LLM APIs** — Integrated via clients layer
- **Subprocess execution** — OS-level process management (Python `subprocess` module)
- **Platform-specific operations** — Handled via `platform` module detection

## Key Call Relationships
```
usage_api.py (entry)
  ├→ session/ (state transitions)
  ├→ clients/ (multi-protocol communication)
  ├→ state/ (persistence)
  ├→ hooks/ (lifecycle events)
  ├→ notifications/ (event dispatch)
  └→ ide/ (editor integration)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence across all modules
- **`./askr/clients/`** — Protocol changes impact CLI, IDE, and external integrations
- **`./askr/hooks/`** — Hook signature changes cascade through all lifecycle consumers
- **`./askr/notifications/`** — Event type additions require updates in all listeners

## Configuration
- Platform detection via `platform` module
- Environment variables via `os` module
- JSON-based configuration in state/snapshot directories
