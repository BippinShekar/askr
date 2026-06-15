# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:43 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to session and state managers

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, execution context, and API interactions
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history and execution context across invocations

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Handles request/response serialization for external AI services

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE interactions
- Manages file operations and code context injection

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates
- Likely integrates with system notifications or logging

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle events
- Triggers on state changes, completion, or errors

**QA Module** (`./askr/qa/`)
- Quality assurance and validation logic
- Likely validates LLM outputs or session integrity

**Utilities** (`./askr/utils/`)
- Shared helper functions (JSON parsing, file I/O, formatting)

## Data Stores
- **`./askr_state/`** — Local filesystem storage for session state, conversation history, and execution artifacts
- **External LLM APIs** — Integrated via `./askr/clients/` (credentials likely environment-based)

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) [reads/writes ./askr_state/]
    → Clients (./askr/clients/) [calls external LLM APIs]
    → IDE (./askr/ide/) [file operations]
    → Hooks (./askr/hooks/) [event callbacks]
    → Notifications (./askr/notifications/) [user feedback]
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any changes to state schema affect session persistence and recovery; used by CLI, session, and hooks
- **`./askr/clients/`** — LLM request/response contracts; changes break all client integrations
- **`./askr/utils/`** — Shared utilities; changes propagate across all modules
- **`./askr/hooks/`** — Event signatures; changes require updates in session and state modules

## Build/Environment
- Python package structure with `__pycache__` directories
- Virtual environment at `./venv`
- Stress tests in `./stress-tests/` for load/reliability validation
