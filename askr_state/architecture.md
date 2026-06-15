# Architecture

*Auto-generated at checkpoint — 2026-06-15 22:08 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles notifications, and provides QA/IDE integration for code analysis and generation workflows.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution entry point; orchestrates session lifecycle, subprocess management, and platform-specific operations

## Core Modules

**Session Management** (`./askr/session/`)
- Manages conversation state, session persistence, and usage tracking
- `usage_api.py` coordinates subprocess execution and OS interactions

**CLI** (`./askr/cli/`)
- Command-line interface and argument parsing
- Routes user input to appropriate handlers

**State Management** (`./askr/state/`)
- Maintains application state and session context
- Persists to `./askr_state/` directory

**Clients** (`./askr/clients/`)
- External service integrations (LLM APIs, code analysis tools)
- Handles authentication and API communication

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Decoupled from core logic

**IDE Integration** (`./askr/ide/`)
- Editor/IDE plugin support and communication
- Language server protocol or similar integration

**QA** (`./askr/qa/`)
- Code quality checks, testing, validation
- Runs analysis on generated/modified code

**Hooks** (`./askr/hooks/`)
- Event handlers for lifecycle events (pre/post execution)
- Extensibility points for custom workflows

**Utilities** (`./askr/utils/`)
- Shared helper functions, logging, formatting

## Data Stores
- **`./askr_state/`** — Persistent session and state data (JSON/config format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./Formula/`** — Template or configuration definitions (purpose unclear from structure)

## External Integrations
- LLM APIs (via `./askr/clients/`)
- Subprocess execution (OS-level code execution)
- IDE/editor communication (via `./askr/ide/`)

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state coordination)
  ├→ cli/ (user input)
  ├→ state/ (persistence)
  ├→ clients/ (external APIs)
  ├→ notifications/ (user feedback)
  ├→ qa/ (validation)
  ├→ ide/ (editor integration)
  └→ hooks/ (event dispatch)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — API contract changes impact all modules calling external services
- **`./askr/session/usage_api.py`** — Core orchestration; changes propagate across all workflows
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers

## Testing & Validation
- **`./tests/`** — Unit and integration tests
- **`./stress-tests/`** — Load/performance testing
