# Architecture

*Auto-generated at checkpoint — 2026-06-12 21:40 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- `./askr/cli/` — Command-line interface handlers that dispatch to session and client modules

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, platform detection
- Manages active session state and coordinates between CLI and clients

**Client Layer** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles request/response serialization to external AI services

**State Management** (`./askr/state/`)
- Persists and retrieves session state (likely JSON/file-based in `./askr_state/`)
- Tracks conversation history, user context, and execution results

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions
- Likely handles file operations, syntax awareness, or editor protocol communication

**Notifications** (`./askr/notifications/`)
- Delivers async alerts (completion status, errors, results)
- Decoupled from main execution flow

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)
- Enables extensibility without modifying core modules

**QA** (`./askr/qa/`)
- Validation and testing utilities for agent responses
- Likely includes prompt validation or output verification

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, environment setup)

## Data Stores
- `./askr_state/` — File-based session state persistence (JSON or similar)
- In-memory session objects during execution

## External Integrations
- LLM providers via `./askr/clients/` (API calls)
- Subprocess execution for code/shell commands
- IDE/editor communication via `./askr/ide/`

## Key Relationships
```
CLI → Session (usage_api.py) → State + Clients + IDE
                            ↓
                      Notifications, Hooks, QA
```

- `usage_api.py` is the orchestrator; all major flows pass through it
- Clients are stateless; state management is centralized
- Hooks enable side effects without coupling modules
- IDE module reads/writes files; state module persists decisions

## Shared Interfaces (High Impact)
- `./askr/state/` — Any state schema changes affect session, hooks, and clients
- `./askr/clients/` — LLM response format changes propagate to QA and session handlers
- `./askr/session/usage_api.py` — Core API; changes affect CLI and all downstream modules
