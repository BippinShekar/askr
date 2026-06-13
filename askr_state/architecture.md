# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:03 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Editor/IDE interaction layer
- File operations and code context management

**Notifications** (`./askr/notifications/`)
- User feedback system (alerts, status updates)

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON or similar format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Called via `./askr/clients/` (subprocess execution in `usage_api.py` suggests shell command wrapping)
- **IDE/Editor** — File system operations through `./askr/ide/`
- **System Shell** — `subprocess` module for command execution

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state management)
  ├→ clients/ (LLM communication)
  ├→ state/ (persistence)
  ├→ ide/ (file operations)
  ├→ notifications/ (user feedback)
  ├→ hooks/ (lifecycle events)
  └→ utils/ (shared helpers)

cli/ → session/ → state/ + clients/
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — LLM response format changes propagate to session, hooks, and QA
- **`./askr/utils/`** — Utility function signatures affect all dependent modules
- **`./askr/session/usage_api.py`** — Core execution contract; changes affect CLI routing and state transitions

## Build/Environment
- Python virtual environment in `./venv/`
- Stress tests in `./stress-tests/` for load validation
- Git history in `./.git/`
