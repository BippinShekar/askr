# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:54 UTC*

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

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely multiple provider support)
- Translates between internal message formats and external API contracts

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file system operations
- Enables in-editor code suggestions and navigation

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle events

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON-based from `usage_api.py` imports)
- **`./Formula/`** — Likely template or configuration definitions

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (subprocess calls to external APIs)
- **IDE/Editor** — Via `./askr/ide/` (file system and editor protocol integration)
- **System Environment** — Platform detection and subprocess management

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init, lifecycle)
  ├→ state/ (persistence layer)
  ├→ clients/ (LLM communication)
  ├→ ide/ (code operations)
  ├→ notifications/ (user feedback)
  └→ hooks/ (event dispatch)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence and all consumers
- **`./askr/clients/`** — Message format changes impact CLI, IDE, and session modules
- **`./askr/session/usage_api.py`** — Core orchestration; changes propagate to all entry points
- **`./askr/utils/`** — Utility modifications affect all dependent modules

## Testing & Stress
- `./stress-tests/` — Load/performance validation suite
- `./askr/qa/` — Unit and integration test utilities
