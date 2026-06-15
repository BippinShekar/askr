# Architecture

*Auto-generated at checkpoint — 2026-06-15 09:57 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that invoke session and state management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, platform detection
- Manages active development contexts and LLM interaction state

**State Management** (`./askr/state/`)
- Persistent storage of session data, conversation history, and agent decisions
- Serializes/deserializes state to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Handles API communication, token management, and response parsing

**IDE/Editor Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor state synchronization
- Bridges between agent decisions and actual code modifications

**Notifications** (`./askr/notifications/`)
- User alerts for long-running operations, errors, and completion events

**QA/Testing** (`./askr/qa/`)
- Test execution, validation, and result reporting

**Hooks** (`./askr/hooks/`)
- Pre/post-execution callbacks for extensibility

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction snapshots for debugging/replay
- **`./.claude/`** — Agent-specific metadata or configuration

## External Integrations
- **LLM APIs** — Via `./askr/clients/` adapters
- **Subprocess execution** — OS-level command invocation (Python `subprocess` module)
- **File system** — Code reading/writing via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (manages context)
  ├→ state/ (persists data)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file operations)
  ├→ notifications/ (user feedback)
  └→ qa/ (validation)

cli/ → session/ → state/ + clients/
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and multi-client consistency
- **`./askr/clients/`** — LLM response format changes cascade to session parsing and IDE integration
- **`./askr/utils/`** — Shared utilities used across all modules; breaking changes propagate widely
