# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:21 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata

## Core Modules

**Session Management** (`./askr/session/`)
- Orchestrates conversation state, user interactions, and LLM request/response cycles
- `usage_api.py` coordinates subprocess calls and environment detection

**CLI Interface** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate handlers

**State Management** (`./askr/state/`)
- Persists session data to `./askr_state/` directory
- Tracks conversation history, context, and agent decisions

**Client Integrations** (`./askr/clients/`)
- LLM provider adapters (API clients for external models)
- Handles request formatting and response parsing

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor interactions
- Bridges agent decisions to actual code modifications

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle (pre/post execution, state changes)
- Enables extensibility without core modifications

**Notifications** (`./askr/notifications/`)
- User feedback delivery (console, file, external channels)

**QA Module** (`./askr/qa/`)
- Test execution and validation of agent-generated code

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/structured files)
- **`./.llm_snapshot/`** — LLM interaction snapshots for debugging/replay
- **`./.claude/`** — Agent-specific metadata and configuration

## External Integrations
- **LLM APIs** — Via `./askr/clients/` adapters
- **Subprocess execution** — OS-level command invocation (platform-aware)
- **File system** — Code reading/writing through `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ↓
session/ (orchestration)
  ├→ clients/ (LLM requests)
  ├→ state/ (persistence)
  ├→ ide/ (file operations)
  ├→ hooks/ (events)
  ├→ notifications/ (output)
  └→ qa/ (validation)
cli/ (user input) → session/
utils/ (shared) ← all modules
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Session schema changes affect all modules reading/writing state
- **`./askr/clients/`** — LLM response format changes impact session parsing logic
- **`./askr/utils/`** — Logging/helper changes propagate across all modules
- **`./askr/hooks/`** — Event signatures affect all hook consumers

## Configuration
- Platform detection in `usage_api.py` (subprocess, OS-specific paths)
- State directory: `./askr_state/`
