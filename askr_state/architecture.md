# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:26 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with code analysis, notifications, and state persistence.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- `./askr/cli/` — Command-line interface layer (specific entry scripts not detailed in imports)

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session execution, handles subprocess spawning and OS-level operations
- Manages session state lifecycle and persistence

**State Management** (`./askr/state/`)
- Maintains in-memory and persisted state (`./askr_state/` directory)
- Tracks session context, user interactions, and code analysis results

**Client Integrations** (`./askr/clients/`)
- Abstracts external API calls (likely LLM providers, code analysis services)
- Decouples service implementations from core logic

**IDE Integration** (`./askr/ide/`)
- Bridges code editor/IDE communication
- Handles file operations and editor state synchronization

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decoupled from core session logic

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic
- Likely used during development and stress-testing

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks (pre/post execution, state changes)
- Extensibility mechanism for custom workflows

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- `./askr_state/` — Persistent session state (JSON or similar format based on `usage_api.py` imports)
- In-memory state objects in `./askr/state/`

## External Integrations
- Subprocess execution (OS commands, tool invocation)
- Platform-specific behavior (Windows/Linux/macOS detection)
- IDE/editor communication via `./askr/ide/`
- External APIs via `./askr/clients/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (external services)
  ├→ ide/ (editor sync)
  ├→ notifications/ (user feedback)
  └→ hooks/ (event dispatch)
```

## Shared Interfaces
- `./askr/state/` — Any state schema changes affect session persistence and all modules reading state
- `./askr/clients/` — API contract changes impact all features using external services
- `./askr/utils/` — Utility function signatures affect all dependent modules
- `./askr/hooks/` — Hook event definitions affect all listeners

## Development Notes
- `./stress-tests/` — Load/performance testing suite
- `./venv/` — Python virtual environment
- `./.llm_snapshot/` — Likely codebase snapshots for LLM context
