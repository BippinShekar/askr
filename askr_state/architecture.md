# Architecture

*Auto-generated at checkpoint — 2026-06-15 22:18 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Translates requests to provider-specific APIs

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file operations
- Manages workspace context and file system access

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**QA/Testing** (`./askr/qa/`)
- Validation and testing utilities for agent outputs

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/structured format)
- **`./.llm_snapshot/`** — LLM interaction snapshots/logs
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM Providers** — Accessed via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess Execution** — System commands via Python `subprocess` module
- **File System** — IDE workspace files accessed through `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state management)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file/workspace context)
  ├→ state/ (persistence to ./askr_state/)
  ├→ hooks/ (lifecycle events)
  ├→ notifications/ (user feedback)
  └→ subprocess (system execution)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Provider API contracts used by session and CLI modules
- **`./askr/session/usage_api.py`** — Central orchestrator; changes propagate to all entry points
- **`./askr/hooks/`** — Event signatures affect all lifecycle-dependent modules

## Testing
- **`./tests/`** — Unit and integration tests
- **`./stress-tests/`** — Load/performance validation
