# Architecture

*Auto-generated at checkpoint — 2026-06-15 22:30 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles user queries, and integrates with external AI clients through a modular hook and notification system.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions and processes usage metrics via subprocess calls and platform detection.
- **CLI commands** — `./askr/cli/` directory contains command handlers that trigger session workflows.

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state persistence, and usage tracking
- `usage_api.py` coordinates subprocess execution and platform-specific operations

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Persists to `./askr_state/` directory

**Clients** (`./askr/clients/`)
- Abstractions for external AI services (LLM providers)
- Handles request/response translation to provider APIs

**Hooks** (`./askr/hooks/`)
- Event-driven system for intercepting and extending behavior
- Allows plugins to react to session events without modifying core logic

**Notifications** (`./askr/notifications/`)
- Delivers alerts and status updates to users
- Decoupled from core session logic

**IDE Integration** (`./askr/ide/`)
- Bridges between Askr and IDE environments
- Handles file operations and editor communication

**QA** (`./askr/qa/`)
- Quality assurance and validation logic
- Tests generated code or responses

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, etc.)

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON or similar)
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **AI Clients** — Multiple LLM providers via `./askr/clients/`
- **Subprocess execution** — OS-level command invocation (platform-aware)
- **IDE APIs** — Via `./askr/ide/` module

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/) 
    → State (./askr/state/) + Hooks (./askr/hooks/)
    → Clients (./askr/clients/) [external LLMs]
    → Notifications (./askr/notifications/)
    → IDE (./askr/ide/)
    → QA (./askr/qa/)
```

## Shared Interfaces (High Impact)
- **`./askr/clients/`** — Client abstraction layer; changes affect all LLM integrations
- **`./askr/state/`** — State schema; changes break session persistence
- **`./askr/hooks/`** — Hook contract; changes affect all event subscribers
- **`./askr/utils/`** — Utility signatures; used across all modules

## Testing
- `./tests/` — Unit and integration tests
- `./stress-tests/` — Performance and load testing
