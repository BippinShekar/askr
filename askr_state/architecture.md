# Architecture

*Auto-generated at checkpoint — 2026-06-12 14:49 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session lifecycle, subprocess orchestration, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session execution, manages subprocess calls, tracks platform context
- Owns session lifecycle and state transitions

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Interfaces with `./askr_state/` directory for state storage

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider communication
- Multiple client implementations for different AI backends

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions
- Handles file operations and editor-specific protocols

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decouples event emission from delivery mechanism

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle events
- Enables extensibility without modifying core session logic

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation helpers

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state storage (filesystem-based)
- **`./Formula/`** — Configuration or template definitions (purpose inferred from structure)

## External Integrations
- **Subprocess execution** — Delegates to system shell via `subprocess` module
- **LLM clients** — Multiple provider support via `./askr/clients/`
- **IDE protocols** — Editor communication via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle control)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (editor integration)
  ├→ hooks/ (event dispatch)
  └→ notifications/ (user feedback)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/session/`** — Session contract; changes affect CLI routing and state management
- **`./askr/state/`** — State schema; changes cascade to all modules reading/writing state
- **`./askr/clients/`** — Client abstraction; changes affect LLM provider switching
- **`./askr/hooks/`** — Event signatures; changes affect all listeners across modules

## Notes
- State is decoupled from session logic via `./askr/state/` abstraction
- Notifications and hooks enable loose coupling for extensibility
- Platform detection in `usage_api.py` suggests cross-OS support (Windows/Unix)
