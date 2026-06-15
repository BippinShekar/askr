# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:33 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session continuity

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles request/response formatting for external AI services

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file operations
- Manages workspace context and code analysis

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates

**QA/Testing** (`./askr/qa/`)
- Quality assurance and validation logic

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/serialized format)
- **External LLM APIs** — Called via `./askr/clients/` (credentials likely from environment variables)

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init & lifecycle)
  ├→ state/ (persistence layer)
  ├→ clients/ (LLM communication)
  ├→ ide/ (workspace context)
  ├→ notifications/ (user feedback)
  └→ cli/ (command routing)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — Client interface changes impact all LLM-dependent modules (session, ide, qa)
- **`./askr/utils/`** — Utility function signatures affect all consumers across modules
- **`./askr/session/usage_api.py`** — Core orchestration; changes propagate to CLI and state management

## External Dependencies
- Subprocess execution (platform-aware)
- Environment variables for credentials/config
- File system for state persistence
