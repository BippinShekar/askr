# Architecture

*Auto-generated at checkpoint — 2026-06-14 08:57 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely multiple client types)
- Translates requests to provider-specific APIs

**IDE Integration** (`./askr/ide/`)
- Bridges code editor/IDE interactions
- Manages file operations and editor state synchronization

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction snapshots/cache
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **LLM Providers** — Integrated via `./askr/clients/` (subprocess calls to external APIs)
- **IDEs/Editors** — Managed through `./askr/ide/`
- **System Shell** — `subprocess` module used in `usage_api.py` for command execution

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ hooks/ (event dispatch)
  └→ notifications/ (user feedback)

cli/ (user commands)
  └→ session/ → state/ → clients/

ide/ (editor integration)
  └→ state/ (sync file changes)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery, persistence, and all modules reading state
- **`./askr/clients/`** — Client interface changes impact CLI, session management, and hooks
- **`./askr/utils/`** — Utility function signatures affect all dependent modules
- **`./askr/hooks/`** — Hook event contracts affect session lifecycle and notification dispatch
