# Architecture

*Auto-generated at checkpoint — 2026-06-12 14:47 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` modules expose command handlers triggered by user input

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization across CLI invocations

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles request/response formatting for external AI services

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file system operations
- Enables in-editor code suggestions and navigation

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decouples notification logic from core session handling

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic for session outputs

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers (pre/post session, pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./.claude/`** — Agent-specific metadata or configuration

## External Integrations
- **LLM APIs** — via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — spawns external tools/compilers
- **File system** — reads/writes code files through `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init & lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file operations)
  ├→ hooks/ (event dispatch)
  ├→ notifications/ (user feedback)
  └→ utils/ (shared helpers)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Client interface changes propagate to all LLM-dependent features
- **`./askr/utils/`** — Utility function signatures impact all consumers
- **`./askr/hooks/`** — Hook event definitions affect session lifecycle across modules
