# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:44 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage, and integrates with IDE/notification systems.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI invocation.

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session lifecycle, subprocess execution, platform detection
- Manages session state persistence and API interactions

**CLI** (`./askr/cli/`)
- Command parsing and routing
- User input handling for interactive workflows

**State Management** (`./askr/state/`)
- Session state tracking and persistence
- Shared state across components

**Clients** (`./askr/clients/`)
- External API clients (LLM providers, backend services)
- Request/response handling for AI interactions

**IDE Integration** (`./askr/ide/`)
- Editor plugin communication
- Code context extraction and injection

**Notifications** (`./askr/notifications/`)
- User alerts and status updates
- Multi-channel delivery (console, IDE, external)

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle
- Pre/post-execution handlers

**QA** (`./askr/qa/`)
- Testing and validation utilities
- Response quality checks

**Utilities** (`./askr/utils/`)
- Shared helper functions
- Logging, formatting, file operations

## Data Stores
- `./askr_state/` — Local session state directory (persisted between runs)
- In-memory session objects in `./askr/session/`

## External Integrations
- Subprocess execution (platform-aware via `platform` module)
- IDE communication layer (`./askr/ide/`)
- Backend API clients (`./askr/clients/`)

## Key Relationships
```
usage_api.py (entry)
  ├→ cli/ (parse commands)
  ├→ session/ (manage lifecycle)
  ├→ state/ (persist/load state)
  ├→ clients/ (call external APIs)
  ├→ ide/ (inject code/context)
  ├→ notifications/ (alert user)
  ├→ hooks/ (trigger events)
  └→ utils/ (shared helpers)
```

## Shared Interfaces
- `./askr/state/` — All modules read/write session state; changes affect session persistence
- `./askr/clients/` — API contract changes impact all modules calling external services
- `./askr/utils/` — Utility function signatures affect all consumers
- `./askr/session/usage_api.py` — Core orchestration; changes to subprocess/platform handling cascade to CLI behavior

## Configuration
- `./askr_state/` — Runtime state directory
- `./.llm_snapshot/` — Cached LLM responses/context
- `./.claude/` — Agent-specific metadata
