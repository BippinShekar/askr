# Architecture

*Auto-generated at checkpoint — 2026-06-14 09:08 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics via subprocess calls and platform detection
- **CLI commands** — `./askr/cli/` modules expose user-facing commands that instantiate session and state managers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Tracks execution metrics, spawns subprocess operations
- Manages session lifecycle and context persistence

**State Management** (`./askr/state/`)
- Maintains in-memory and persisted state (`./askr_state/` directory)
- Tracks conversation history, file modifications, execution results

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Handles API communication, token counting, response parsing

**IDE/Editor Integration** (`./askr/ide/`)
- File system operations, code analysis, syntax awareness
- Bridges between agent decisions and actual code modifications

**Notifications** (`./askr/notifications/`)
- User feedback mechanisms (console, webhooks, or external services)
- Status updates during long-running operations

**QA/Validation** (`./askr/qa/`)
- Test execution, output validation
- Verifies agent-generated code changes

**Hooks** (`./askr/hooks/`)
- Pre/post-execution callbacks
- Integration points for external tools

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/pickle format likely)
- **In-memory state** — Active session context in `./askr/state/`
- **`.claude/`, `.llm_snapshot/`** — Agent metadata and snapshots

## External Integrations
- **LLM APIs** — Via `./askr/clients/`
- **Subprocess execution** — For code testing and system commands
- **File system** — Direct read/write via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ↓
session/ (lifecycle)
  ↓
state/ (context)
  ├→ clients/ (LLM calls)
  ├→ ide/ (code changes)
  ├→ qa/ (validation)
  └→ notifications/ (feedback)

hooks/ (cross-cutting)
utils/ (shared)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session, clients, and IDE modules
- **`./askr/clients/`** — LLM response format changes cascade to session and QA
- **`./askr/utils/`** — Logging/formatting utilities used across all modules
- **`./askr_state/` persistence format** — Changes require migration logic

## Testing
- `./stress-tests/` — Load/performance validation
