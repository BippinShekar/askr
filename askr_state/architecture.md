# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:24 UTC*

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
- Handles API calls to external AI services

**IDE Integration** (`./askr/ide/`)
- Bridges between CLI and IDE environments
- Manages editor-specific interactions and file operations

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle events (pre/post execution)

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar format)
- **External LLM APIs** — Called via `./askr/clients/` for AI inference

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) → ./askr_state/
    → Clients (./askr/clients/) → External LLM APIs
    → IDE (./askr/ide/)
    → Hooks (./askr/hooks/)
    → Notifications (./askr/notifications/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — Client interface changes propagate to all LLM-dependent modules
- **`./askr/session/usage_api.py`** — Core session contract; changes affect CLI routing and all downstream services
- **`./askr/utils/`** — Shared utilities; breaking changes cascade across all modules

## External Dependencies
- Python subprocess module for execution
- Platform detection (OS-specific behavior)
- LLM provider APIs (abstracted via clients)
