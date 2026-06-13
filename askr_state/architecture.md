# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:48 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages session lifecycle and state transitions

**State Management** (`./askr/state/`)
- Persistent state storage and retrieval
- Tracks session context, user interactions, and agent decisions

**Client Handlers** (`./askr/clients/`)
- Multi-client abstraction layer
- Manages communication with different LLM providers or interfaces

**IDE Integration** (`./askr/ide/`)
- Editor/IDE-specific adapters
- Handles code context extraction and file operations

**Hooks System** (`./askr/hooks/`)
- Event-driven execution points
- Triggers actions on session events (start, end, state changes)

**QA Module** (`./askr/qa/`)
- Quality assurance and validation logic
- Tests generated code or responses

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Handles delivery across channels

**Utilities** (`./askr/utils/`)
- Shared helper functions
- Logging, formatting, common operations

## Data Stores
- **`./askr_state/`** — Local session state directory; persists session data between runs
- **`./.llm_snapshot/`** — LLM interaction snapshots; caches or logs API exchanges
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM Clients** — Abstracted via `./askr/clients/`; supports multiple providers
- **Subprocess Execution** — Via `usage_api.py`; runs shell commands and external tools
- **IDE/Editor APIs** — Via `./askr/ide/`; reads/writes code files

## Key Call Chains
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/)
    → Clients (./askr/clients/)
    → Hooks (./askr/hooks/) [event triggers]
    → IDE (./askr/ide/) [file operations]
    → QA (./askr/qa/) [validation]
    → Notifications (./askr/notifications/) [user feedback]
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — All modules depend on state schema; changes break session persistence
- **`./askr/clients/`** — Client protocol changes affect all LLM interactions
- **`./askr/hooks/`** — Hook signatures affect all event subscribers
- **`./askr/utils/`** — Utility changes propagate across all modules

## Testing & Stress
- **`./stress-tests/`** — Load and reliability tests; validates session handling under concurrent load
