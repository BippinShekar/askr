# Architecture

*Auto-generated at checkpoint — 2026-06-15 09:01 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session state, lifecycle, and API interactions
- `usage_api.py` orchestrates subprocess execution and platform detection
- Persists session data to `./askr_state/`

**State Management** (`./askr/state/`)
- Maintains in-memory and persistent application state
- Interfaces with `./askr_state/` for serialization

**Client Handlers** (`./askr/clients/`)
- Abstracts multiple LLM client implementations
- Manages API communication and response handling

**IDE Integration** (`./askr/ide/`)
- Provides editor/IDE interaction capabilities
- Handles file operations and workspace context

**Notifications** (`./askr/notifications/`)
- Delivers user-facing messages and alerts
- Decouples notification logic from core services

**Hooks** (`./askr/hooks/`)
- Event-driven system for session lifecycle callbacks
- Enables extensibility without modifying core logic

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation helpers

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (supports multiple providers)
- **Subprocess execution** — OS-level command invocation via `usage_api.py`
- **File system** — IDE integration reads/writes workspace files

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/)
    → Clients (./askr/clients/)
    → IDE (./askr/ide/)
    → Hooks (./askr/hooks/)
    → Notifications (./askr/notifications/)
```

Session is the orchestrator; it coordinates state persistence, client communication, IDE operations, and event callbacks.

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — Client interface changes propagate to session and CLI layers
- **`./askr/hooks/`** — Hook signatures affect all event subscribers across modules
- **`./askr_state/`** — Data format changes break session recovery and state migration

## Build/Environment
- Python package structure with `__pycache__` directories
- Virtual environment at `./venv/`
- Stress tests in `./stress-tests/` for load validation
