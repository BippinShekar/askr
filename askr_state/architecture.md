# Architecture

*Auto-generated at checkpoint — 2026-06-15 11:25 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization across CLI invocations

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Handles request/response formatting and error handling

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE communication
- Manages code context and file operations

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates
- Likely integrates with system notification APIs

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle events (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state storage (JSON or similar)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **System Subprocess** — `usage_api.py` spawns child processes for code execution
- **IDE/Editor** — Via `./askr/ide/` module
- **System Notifications** — Via `./askr/notifications/`

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) → ./askr_state/
    → Clients (./askr/clients/) → LLM providers
    → IDE (./askr/ide/) → file operations
    → Hooks (./askr/hooks/) → event handlers
    → Notifications (./askr/notifications/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — State schema changes affect session persistence across all modules
- **`./askr/clients/`** — Client interface changes impact all LLM communication
- **`./askr/session/usage_api.py`** — Central orchestrator; changes cascade to CLI and state management
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers
