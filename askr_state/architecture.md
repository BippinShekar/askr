# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:56 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions and tracks usage metrics via subprocess calls and platform detection.
- **`./askr/cli/`** — Command-line interface layer; routes user commands to appropriate handlers.

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` is the main entry point for session operations

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Persists to `./askr_state/` directory
- Shared state interface used by all modules

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication
- Multiple client implementations for different AI backends
- Called by session and CLI layers

**IDE Integration** (`./askr/ide/`)
- Handles editor/IDE communication
- Bridges between Askr and development environments

**Notifications** (`./askr/notifications/`)
- Delivers user-facing messages and alerts
- Consumed by CLI and session handlers

**Hooks** (`./askr/hooks/`)
- Event-driven execution points
- Triggered during session lifecycle events

**QA Module** (`./askr/qa/`)
- Quality assurance and validation logic
- Tests agent outputs before execution

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules
- Logging, formatting, common operations

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON-based)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (Claude, other AI backends)
- **Subprocess Execution** — Platform-specific command execution in `usage_api.py`
- **File System** — State persistence and snapshot storage

## Key Call Chains
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/)
    → Clients (./askr/clients/)
    → QA (./askr/qa/)
    → Hooks (./askr/hooks/)
    → Notifications (./askr/notifications/)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — All modules depend on state schema; changes affect persistence and all consumers
- **`./askr/clients/`** — Client interface used by session and CLI; changes break LLM communication
- **`./askr/notifications/`** — Output interface; changes affect all user-facing messages
- **`./askr_state/` schema** — Persistent format; breaking changes require migration logic

## Testing
- **`./stress-tests/`** — Load and integration tests
- **`./askr/qa/`** — Validation before execution
