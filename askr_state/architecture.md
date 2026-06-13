# Architecture

*Auto-generated at checkpoint — 2026-06-13 15:24 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages session state lifecycle and inter-process communication

**State Management** (`./askr/state/`)
- Persistent state storage and retrieval
- Coordinates with `./askr_state/` directory for state artifacts

**Client Handlers** (`./askr/clients/`)
- Multi-client abstraction layer for LLM interactions
- Implements provider-specific logic (API calls, authentication)

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE communication
- Handles file operations and workspace context

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Alerts for session state changes and completions

**Hooks** (`./askr/hooks/`)
- Pre/post-execution lifecycle hooks
- Integration points for custom behaviors

**QA/Testing** (`./askr/qa/`)
- Test validation and quality assurance workflows

**Utilities** (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Session state persistence (likely JSON/YAML artifacts)
- **`./.llm_snapshot/`** — LLM interaction snapshots/caching
- **`./.claude/`** — Claude-specific configuration/context

## External Integrations
- **LLM Clients** — Multiple provider support via `./askr/clients/`
- **Subprocess/OS** — Platform-aware execution via `usage_api.py`
- **IDE/Editor APIs** — Via `./askr/ide/`

## Key Call Relationships
```
usage_api.py (entry)
  ├→ session/ (state lifecycle)
  ├→ clients/ (LLM communication)
  ├→ state/ (persistence)
  ├→ ide/ (workspace context)
  ├→ hooks/ (lifecycle events)
  ├→ notifications/ (event dispatch)
  └→ utils/ (shared helpers)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence, clients, and IDE integration
- **`./askr/clients/`** — Client protocol changes impact `usage_api.py`, hooks, and notifications
- **`./askr/utils/`** — Utility modifications cascade across all modules
- **`./askr_state/`** — State artifact format changes require updates to state/ and session/ modules
