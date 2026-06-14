# Architecture

*Auto-generated at checkpoint — 2026-06-14 08:59 UTC*

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
- Maintains conversation history and execution context

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely multiple AI backends)
- Translates between internal message format and provider APIs

**CLI Interface** (`./askr/cli/`)
- Command parsing and routing
- User-facing command definitions

**IDE Integration** (`./askr/ide/`)
- Editor/IDE communication layer
- Likely handles code context extraction and file operations

**Notifications** (`./askr/notifications/`)
- Event-driven alerts for session state changes
- Async notification delivery

**QA Module** (`./askr/qa/`)
- Test execution and validation
- Quality assurance for generated code

**Hooks** (`./askr/hooks/`)
- Lifecycle callbacks (pre/post execution, state changes)
- Extension points for custom behavior

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/structured format)
- **`./.llm_snapshot/`** — LLM interaction snapshots/logs
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM Providers** — Abstracted via `./askr/clients/`; subprocess execution suggests local model support
- **IDE/Editors** — Via `./askr/ide/` module
- **System Shell** — Direct subprocess calls from `usage_api.py`

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) → ./askr_state/
    → Clients (./askr/clients/) → LLM providers
    → IDE (./askr/ide/) → Editor context
    → QA (./askr/qa/) → Validation
    → Notifications (./askr/notifications/)
    → Hooks (./askr/hooks/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — State schema changes affect session persistence across all modules
- **`./askr/clients/`** — LLM message format changes propagate to CLI, session, and QA
- **`./askr/session/usage_api.py`** — Core execution contract; changes affect all entry points
- **`./askr/utils/`** — Utility function signatures impact all consumers
