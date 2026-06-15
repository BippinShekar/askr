# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:55 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py`: Coordinates session state, subprocess execution, and platform detection
- Manages session lifecycle and inter-process communication

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Interfaces with `./askr_state/` for state storage

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations
- Manages API communication with external AI services

**IDE Integration** (`./askr/ide/`)
- Handles editor/IDE-specific operations
- Bridges between session logic and development environment

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state storage (filesystem-based)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Configuration and metadata

## External Integrations
- LLM providers via `./askr/clients/` (API-based)
- Subprocess execution for development tools
- Platform-specific OS operations (via `platform` and `subprocess` modules)

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state coordination)
  ├→ state/ (persistence layer)
  ├→ clients/ (LLM communication)
  ├→ ide/ (editor operations)
  ├→ notifications/ (user feedback)
  └→ hooks/ (event callbacks)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any changes to state schema affect session recovery and persistence across all modules
- **`./askr/clients/`** — LLM provider interface changes propagate to session logic and IDE integration
- **`./askr/session/usage_api.py`** — Central orchestrator; changes affect all dependent modules
- **`./askr/hooks/`** — Event contract changes impact session lifecycle across all listeners

## Build/Environment
- Python package structure with `__pycache__` directories
- Virtual environment at `./venv/`
- Stress tests available in `./stress-tests/`
