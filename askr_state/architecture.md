# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:28 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to session and state managers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, platform detection
- Manages active session state and coordinates with state persistence layer

**State Management** (`./askr/state/`)
- Persists and retrieves session data (likely JSON-based in `./askr_state/` directory)
- Tracks conversation history, user context, and execution state

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (API communication, request/response handling)
- Abstracts different AI model providers

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, editor communication
- Bridges between session context and user's development environment

**Notifications** (`./askr/notifications/`)
- Event-driven alerts for session state changes, errors, completions

**Hooks** (`./askr/hooks/`)
- Lifecycle callbacks (pre/post execution, state transitions)

**QA/Testing** (`./askr/qa/`)
- Validation and test execution within sessions

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, environment utilities)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar)
- **In-memory state** — Active session context during execution

## External Integrations
- **LLM APIs** — Via `./askr/clients/` adapters
- **Subprocess execution** — System commands via `subprocess` module
- **File system** — Code reading/writing via IDE module

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file operations)
  ├→ hooks/ (callbacks)
  └→ notifications/ (events)

cli/ → session/ → state/ + clients/
```

## Shared Interfaces (High Impact)
- **`./askr/session/`** — Session protocol; changes affect CLI, state, and clients
- **`./askr/state/`** — State schema; changes cascade to all modules reading/writing state
- **`./askr/clients/`** — LLM request/response contracts; affects session and hooks
- **`./askr/utils/`** — Shared utilities; used across all modules

## Execution Flow
1. CLI invokes `usage_api.py` with user command
2. Session manager initializes state from `./askr_state/`
3. Client sends request to LLM via `./askr/clients/`
4. IDE module executes file operations or subprocess commands
5. Hooks trigger notifications and state updates
6. State persisted back to disk
