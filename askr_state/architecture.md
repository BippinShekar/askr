# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:36 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with hooks, notifications, and state persistence.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; handles session initialization, subprocess management, and platform-specific operations

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle and usage tracking via `usage_api.py`
- Coordinates state persistence and retrieval

**CLI** (`./askr/cli/`)
- Command-line interface layer; parses user input and routes to appropriate handlers

**State Management** (`./askr/state/`)
- Maintains application state; persists to `./askr_state/` directory
- Shared state interface consumed by session, hooks, and notifications

**Clients** (`./askr/clients/`)
- External service integrations (likely LLM APIs, version control)
- Abstracts communication with remote systems

**Hooks** (`./askr/hooks/`)
- Event-driven handlers triggered during session lifecycle
- Integrates with state and notifications

**Notifications** (`./askr/notifications/`)
- Delivers alerts/updates to user; consumes state changes
- Triggered by hooks and session events

**IDE Integration** (`./askr/ide/`)
- Editor/IDE communication layer
- Likely manages file operations and editor state sync

**QA** (`./askr/qa/`)
- Quality assurance/validation logic for generated code or responses

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- `./askr_state/` — Persistent session and application state (JSON or similar)
- `./Formula/` — Configuration or template definitions (purpose unclear; likely immutable reference data)

## External Integrations
- Subprocess execution (via `usage_api.py` — `subprocess` module)
- Platform detection (`platform` module)
- File I/O for state persistence

## Key Relationships
```
usage_api.py (entry)
  ↓
session/ (lifecycle)
  ↓
state/ (shared state store)
  ├→ hooks/ (event handlers)
  ├→ notifications/ (user alerts)
  ├→ clients/ (external APIs)
  └→ ide/ (editor sync)

cli/ → session/ → state/
qa/ ← state/ (validates against state)
```

## Shared Interfaces
- **`./askr/state/`** — All modules read/write here; changes affect session, hooks, notifications, and IDE integration
- **`./askr/clients/`** — Abstract client interfaces; changes propagate to session and hooks
- **`./askr/hooks/`** — Event signatures; changes affect session lifecycle and notifications

## Build/Runtime
- Python 3.x with virtual environment (`./venv/`)
- Stress tests in `./stress-tests/` for load validation
