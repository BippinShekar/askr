# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:46 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks state, and integrates with external clients for code analysis and notifications.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; initializes sessions and tracks usage via subprocess calls and platform detection
- CLI commands routed through `./askr/cli/` — Command parsing and dispatch

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Tracks execution metrics, spawns subprocesses, collects platform/environment data
- Manages session lifecycle and state persistence

**State Management** (`./askr/state/`)
- Maintains application state across execution
- Persists to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- Abstracts external service connections (LLM providers, code analysis tools)
- Pluggable client implementations

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE communication
- Handles code context and file operations

**Notifications** (`./askr/notifications/`)
- Delivers user-facing messages and alerts
- Decoupled from core logic

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- `./askr_state/` — Local state persistence (session data, configuration)
- Environment variables — Platform and runtime configuration
- Subprocess outputs — Captured from external tool invocations

## External Integrations
- Subprocess execution — Delegates to system tools
- Platform detection — OS/environment introspection via `platform` module
- JSON serialization — State and API communication

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (external services)
  ├→ ide/ (editor context)
  ├→ notifications/ (output)
  ├→ hooks/ (event dispatch)
  └→ utils/ (shared helpers)
```

## Shared Interfaces (High Impact)
- `./askr/state/` — State schema changes affect all modules reading/writing state
- `./askr/clients/` — Client interface changes propagate to all integrations
- `./askr/utils/` — Utility function signatures affect all consumers
- `./askr/hooks/` — Hook event contracts affect session lifecycle handlers

## Build/Environment
- `./venv/` — Python virtual environment
- `./stress-tests/` — Load/performance testing suite
- `./.llm_snapshot/` — LLM context snapshots for debugging
