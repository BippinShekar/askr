# Architecture

*Auto-generated at checkpoint — 2026-06-15 09:04 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with context awareness and usage tracking.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution entry point; initializes session tracking and usage metrics via subprocess calls and platform detection.

## Core Modules

**CLI Layer** (`./askr/cli/`)
- Command parsing and user interaction interface
- Routes commands to appropriate session/client handlers

**Session Management** (`./askr/session/`)
- `usage_api.py` — Tracks API usage, platform info, subprocess execution
- Manages session lifecycle and state persistence
- Coordinates between CLI input and backend services

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Persists to `./askr_state/` directory
- Provides state snapshots for context recovery

**Client Integrations** (`./askr/clients/`)
- Abstracts external AI/LLM service communication
- Handles request/response serialization

**IDE Integration** (`./askr/ide/`)
- File system operations and code context extraction
- Editor-specific protocol handlers

**Supporting Services**
- `./askr/hooks/` — Event handlers for session lifecycle
- `./askr/notifications/` — User feedback and alerts
- `./askr/qa/` — Quality assurance and validation
- `./askr/utils/` — Shared utilities (logging, formatting, helpers)

## Data Stores
- `./askr_state/` — Local session state persistence
- `./.llm_snapshot/` — LLM context snapshots for recovery
- `./.claude/` — Claude-specific configuration/cache

## External Integrations
- LLM clients (via `./askr/clients/`)
- Subprocess execution for platform-specific operations
- IDE/editor protocols (via `./askr/ide/`)

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) → ./askr_state/
    → Clients (./askr/clients/)
    → IDE (./askr/ide/)
    → Hooks (./askr/hooks/)
    → Notifications (./askr/notifications/)
```

Session is the orchestrator; it coordinates state persistence, client calls, and IDE operations based on CLI commands.

## Shared Interfaces (High Impact)
- `./askr/state/` — State schema changes affect session persistence and recovery
- `./askr/clients/` — Client protocol changes affect all LLM integrations
- `./askr/utils/` — Utility function signatures affect all dependent modules
- `./askr/session/usage_api.py` — Session initialization affects CLI startup and metrics

## Testing & Stress
- `./stress-tests/` — Load and reliability testing suite
- `./askr/qa/` — Validation logic for responses and state
