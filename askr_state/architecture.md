# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:27 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session state, lifecycle, and API interactions
- `usage_api.py` coordinates subprocess execution and platform detection
- Handles session persistence and recovery

**State Management** (`./askr/state/`)
- Maintains in-memory and persisted application state
- Syncs with `./askr_state/` directory for state snapshots

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely multiple provider support)
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Editor/IDE interaction layer
- Manages code context and file operations

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Alerts for session state changes, errors, completions

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers
- Triggered during session transitions and operations

**QA/Testing** (`./askr/qa/`)
- Test execution and validation
- Code quality checks

**Utilities** (`./askr/utils/`)
- Shared helper functions
- Logging, formatting, common operations

## Data Stores
- **`./askr_state/`** — Persistent session state snapshots
- **`./.llm_snapshot/`** — LLM interaction history/cache
- **`./.claude/`** — Configuration or Claude-specific metadata

## External Integrations
- **Subprocess execution** — Runs development tools, tests, linters
- **LLM APIs** — Multiple client adapters in `./askr/clients/`
- **File system** — Code context, state persistence
- **Platform APIs** — OS-specific operations via `platform` module

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state coordination)
  ├→ clients/ (LLM communication)
  ├→ state/ (persistence)
  ├→ cli/ (command routing)
  ├→ ide/ (code context)
  ├→ hooks/ (event dispatch)
  ├→ notifications/ (alerts)
  └→ qa/ (validation)
```

## Shared Interfaces (High Impact)
- **`./askr/session/usage_api.py`** — Core API contract; changes affect all entry points
- **`./askr/state/`** — State schema changes propagate to persistence layer and all consumers
- **`./askr/clients/`** — LLM response format changes affect session parsing and hooks
- **`./askr/hooks/`** — Event signatures affect all lifecycle-dependent modules (notifications, qa, ide)
