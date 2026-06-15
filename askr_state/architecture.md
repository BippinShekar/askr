# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:49 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface handlers that trigger session creation and state transitions

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages session lifecycle and coordinates with other subsystems

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Interfaces with `./askr_state/` directory for state storage
- Critical for session recovery and continuity

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider communication
- Multiple client implementations for different AI backends
- Consumed by session and CLI modules

**IDE Integration** (`./askr/ide/`)
- Editor/IDE-specific functionality
- Handles code context and file operations

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events
- Triggered by session state changes

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Consumed by CLI and session modules

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (file-based)
- **`./.llm_snapshot/`** — LLM interaction snapshots/cache
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (multiple backend support)
- **Subprocess Execution** — OS-level process management in `usage_api.py`
- **File System** — IDE and state modules read/write project files

## Key Relationships
```
usage_api.py (entry)
  ├→ ./askr/state/ (load/save session)
  ├→ ./askr/clients/ (LLM communication)
  ├→ ./askr/hooks/ (trigger callbacks)
  ├→ ./askr/notifications/ (user feedback)
  └→ ./askr/ide/ (code context)

./askr/cli/
  ├→ usage_api.py (session control)
  └→ ./askr/state/ (state queries)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence, CLI queries, and hooks
- **`./askr/clients/`** — Client interface changes impact session communication and LLM integration
- **`./askr/hooks/`** — Hook signatures affect all event subscribers (notifications, IDE, state)
- **`./askr_state/`** — Storage format changes break session recovery

## Configuration
- Platform detection in `usage_api.py` (Windows/Linux/macOS handling)
- Client selection likely in `./askr/clients/`
