# Architecture

*Auto-generated at checkpoint — 2026-06-13 16:47 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages session state lifecycle and coordinates between CLI and backend services

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely multiple provider support)
- Handles API communication with external AI services

**IDE/Editor Integration** (`./askr/ide/`)
- Code analysis and manipulation interfaces
- Bridges between session context and code editing operations

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Alerts for session state changes, errors, completions

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers
- Triggers on session start/end, state changes

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework
- Likely validates code changes before committing

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar)
- **`./Formula/`** — Configuration or template definitions (purpose unclear; likely formula/prompt templates)

## External Integrations
- **LLM APIs** — Via `./askr/clients/` adapters
- **Subprocess execution** — OS-level code execution (Python, shell commands)
- **IDE/Editor APIs** — Code manipulation through `./askr/ide/`

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) ↔ ./askr_state/
    → Clients (./askr/clients/) → LLM APIs
    → IDE (./askr/ide/) → Code operations
    → QA (./askr/qa/) → Validation
    → Notifications (./askr/notifications/)
    → Hooks (./askr/hooks/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — State schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Client interface changes impact all LLM-dependent modules (session, hooks, QA)
- **`./askr/session/usage_api.py`** — Central orchestrator; changes cascade to all dependent services
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers
