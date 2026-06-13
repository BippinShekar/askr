# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:36 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage, and integrates with IDE/notification systems.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI commands

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session lifecycle, subprocess execution, platform detection
- Manages state persistence and usage metrics

**CLI** (`./askr/cli/`)
- Command parsing and routing
- User input handling

**State Management** (`./askr/state/`)
- Session state persistence (`./askr_state/` directory)
- State serialization/deserialization

**Clients** (`./askr/clients/`)
- External service integrations (likely LLM/API clients)
- Request/response handling

**IDE Integration** (`./askr/ide/`)
- IDE-specific adapters and communication
- Code context extraction

**Notifications** (`./askr/notifications/`)
- User notification delivery (desktop/console)

**Hooks** (`./askr/hooks/`)
- Event handlers and lifecycle callbacks

**QA** (`./askr/qa/`)
- Testing/validation utilities

**Utils** (`./askr/utils/`)
- Shared helper functions

## Data Stores
- `./askr_state/` — Local session state storage (JSON/serialized format)
- Environment variables (platform, config via `os` module)

## External Integrations
- Subprocess execution (platform-specific CLI tools)
- IDE communication (via `./askr/ide/`)
- Notification systems (via `./askr/notifications/`)
- LLM/API clients (via `./askr/clients/`)

## Key Relationships
```
usage_api.py (entry)
  ├→ cli/ (parse commands)
  ├→ session/ (manage lifecycle)
  ├→ state/ (persist/load state)
  ├→ clients/ (call external APIs)
  ├→ ide/ (get code context)
  ├→ notifications/ (alert user)
  └→ hooks/ (trigger callbacks)
```

## Shared Interfaces (High Impact)
- `./askr/state/` — Any state schema changes affect session persistence across all modules
- `./askr/clients/` — API contract changes impact CLI, session, and IDE modules
- `./askr/utils/` — Utility function signatures affect all consumers
- `./askr/session/usage_api.py` — Entry point changes affect CLI routing and subprocess handling

## Build/Environment
- `./venv/` — Python virtual environment
- `./stress-tests/` — Load/performance testing
- `./.llm_snapshot/` — LLM context snapshots (likely for debugging)
