# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:34 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that dispatch to session and client modules

## Core Modules

**Session Management** (`./askr/session/`)
- Owns session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection
- Persists session data to `./askr_state/`

**State Management** (`./askr/state/`)
- Maintains in-memory and persistent session state
- Interfaces with `./askr_state/` directory for serialization
- Shared state object passed between CLI, clients, and hooks

**Clients** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles request/response formatting and API calls
- Consumed by session and CLI modules

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE communication
- Likely handles file operations, diagnostics, and editor state sync

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)
- Triggered by session and CLI modules

**Notifications** (`./askr/notifications/`)
- Delivers user-facing messages and alerts
- Called from session, CLI, and client modules

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic
- Stress tests in `./stress-tests/`

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)
- Low-level dependencies for all modules

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — OS-level process management in `usage_api.py`
- **IDE/Editor protocols** — Via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  │   ├→ state/ (persistence)
  │   ├→ hooks/ (events)
  │   └→ notifications/ (output)
  ├→ cli/ (command dispatch)
  │   ├→ clients/ (LLM calls)
  │   ├→ ide/ (editor sync)
  │   └→ state/ (read/write)
  └→ utils/ (shared)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session, CLI, clients, and persistence
- **`./askr/clients/`** — Client API contract used by session and CLI; changes require adapter updates
- **`./askr/utils/`** — Utility functions imported across all modules; breaking changes cascade widely
- **`./askr_state/` format** — Serialization schema; changes break session recovery
