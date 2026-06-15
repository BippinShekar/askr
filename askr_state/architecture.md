# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:24 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface handlers that route user input to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Main orchestrator; manages session state, subprocess execution, and platform detection
- Coordinates between CLI input, state persistence, and client communication

**State Management** (`./askr/state/`)
- Maintains session state and conversation history
- Persists to `./askr_state/` directory
- Provides state snapshots for recovery and debugging

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Handles request/response serialization and error handling

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE interactions
- Likely manages file operations and code context

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates
- May integrate with system notifications

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle events
- Triggers on state changes or user actions

**QA** (`./askr/qa/`)
- Testing and validation utilities
- Likely includes prompt validation or response quality checks

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state directory
- **`./.llm_snapshot/`** — LLM interaction snapshots for debugging/auditing
- **`./.claude/`** — Configuration or cached credentials

## External Integrations
- LLM providers (via `./askr/clients/`)
- System subprocess execution (Python `subprocess` module)
- Platform-specific operations (via `platform` module)

## Key Relationships
```
CLI (./askr/cli/) 
  → usage_api.py (session orchestrator)
    → state/ (persistence)
    → clients/ (LLM communication)
    → ide/ (code context)
    → hooks/ (event dispatch)
    → notifications/ (user feedback)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session recovery and all modules reading state
- **`./askr/clients/`** — Provider interface changes cascade to all LLM-dependent modules
- **`./askr/session/usage_api.py`** — Central orchestrator; changes affect entire execution flow
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers

## Build/Environment
- Python virtual environment at `./venv/`
- Stress tests in `./stress-tests/` for load validation
