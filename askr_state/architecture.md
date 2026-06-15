# Architecture

*Auto-generated at checkpoint — 2026-06-15 09:00 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks state, and integrates with external clients for code analysis and notifications.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- CLI commands routed through `./askr/cli/` modules

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session execution, subprocess management, platform detection
- Manages session lifecycle and state persistence

**State Management** (`./askr/state/`)
- Maintains application state across execution
- Persisted to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- Pluggable client implementations for external services
- Handles communication with AI/code analysis backends

**IDE Integration** (`./askr/ide/`)
- Editor-specific adapters and protocol handlers
- Bridges between Askr and development environments

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Dispatches alerts to users

**Hooks** (`./askr/hooks/`)
- Event handlers and lifecycle callbacks
- Integrates with session and state changes

**QA/Testing** (`./askr/qa/`)
- Quality assurance and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Persistent session and application state
- **`./.llm_snapshot/`** — LLM context snapshots (likely for prompt caching)
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- Subprocess execution (platform-aware)
- External AI clients via `./askr/clients/`
- IDE protocols via `./askr/ide/`
- Notification backends via `./askr/notifications/`

## Key Call Chains
```
usage_api.py (entry)
  → session lifecycle management
  → state persistence (./askr_state/)
  → client integrations (./askr/clients/)
  → hooks (./askr/hooks/)
  → notifications (./askr/notifications/)
  → IDE adapters (./askr/ide/)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session, hooks, and persistence
- **`./askr/clients/`** — Client protocol changes affect all integrations
- **`./askr/session/usage_api.py`** — Session lifecycle changes cascade to all dependent modules
- **`./askr/hooks/`** — Hook signatures affect session and state modules

## Build/Environment
- Python virtual environment: `./venv/`
- Stress tests: `./stress-tests/` (performance validation)
- Git tracked: `./.git/`
