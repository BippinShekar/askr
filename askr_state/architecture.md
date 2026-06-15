# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:18 UTC*

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
- Handles state serialization/deserialization for session continuity

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles API calls and response parsing

**IDE Integration** (`./askr/ide/`)
- Bridges between Askr and IDE environments
- Manages file operations and editor interactions

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle events

**QA Module** (`./askr/qa/`)
- Quality assurance and validation logic for generated code/responses

**Utilities** (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON or similar format)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — OS-level command execution for code/scripts
- **IDE communication** — File system and editor protocol integration

## Key Relationships
```
usage_api.py (entry)
  ↓
session/ (orchestrates)
  ├→ state/ (persists)
  ├→ clients/ (queries LLM)
  ├→ ide/ (reads/writes files)
  ├→ hooks/ (triggers events)
  └→ notifications/ (alerts user)

cli/ (user commands)
  ↓
session/ (same orchestrator)
```

## Shared Interfaces (High Impact)
- **`./askr/session/`** — All modules depend on session state; changes affect entire system
- **`./askr/state/`** — State schema changes break persistence; affects all session-aware modules
- **`./askr/clients/`** — LLM response format changes propagate to QA, IDE, and notifications
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers

## Configuration
- Environment detection via `platform` and `subprocess` in `usage_api.py`
- State directory: `./askr_state/`
