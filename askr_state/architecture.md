# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:33 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- `./askr/cli/` — Command-line interface handlers that dispatch user commands to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, platform detection
- Manages active session state and coordinates between CLI input and backend services

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Abstracts API communication for AI model interactions

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE communication layer
- Handles file operations and editor state synchronization

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Decouples notification logic from core session handling

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)
- Extensibility points for custom behaviors

**QA** (`./askr/qa/`)
- Testing/validation utilities for agent responses
- Quality assurance checks before execution

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- `./askr_state/` — Local filesystem storage for session state persistence
- In-memory session objects during active execution

## External Integrations
- LLM APIs via `./askr/clients/`
- IDE/editor communication via `./askr/ide/`
- Subprocess execution for code/commands via `usage_api.py`

## Key Relationships
```
CLI (./askr/cli/) 
  → usage_api.py (session entry point)
    → state/ (load/save session)
    → clients/ (LLM queries)
    → ide/ (file operations)
    → hooks/ (lifecycle events)
    → notifications/ (user feedback)
    → qa/ (validation)
```

## Shared Interfaces (High Impact)
- `./askr/state/` — Any state schema changes affect session persistence and recovery
- `./askr/clients/` — LLM response format changes propagate to session logic and QA
- `./askr/session/usage_api.py` — Core session contract; changes affect CLI, hooks, and state management
- `./askr/utils/` — Shared utilities; breaking changes affect all modules
