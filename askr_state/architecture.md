# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:39 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session lifecycle, subprocess orchestration, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session and state management

## Core Modules

**Session Management** (`./askr/session/`)
- Manages conversation state, session lifecycle, and API interactions
- `usage_api.py` orchestrates subprocess calls and platform detection
- Coordinates with state and client modules

**State Management** (`./askr/state/`)
- Persists and retrieves session data
- Likely handles serialization to `./askr_state/` directory
- Maintains conversation history and context

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (API clients)
- Handles authentication and request/response formatting
- Multiple client implementations for different providers

**IDE Integration** (`./askr/ide/`)
- Editor/IDE-specific operations
- File manipulation, syntax awareness, code insertion

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Likely integrates with system notifications or CLI output

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks (pre/post session, on state changes)
- Extensibility mechanism for custom workflows

**QA** (`./askr/qa/`)
- Testing and validation utilities
- Code quality checks or response validation

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation snapshots
- **`./.claude/`** — Agent-specific metadata or configuration

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — System commands via `subprocess` module
- **File system** — IDE file operations via `./askr/ide/`

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/)
    → Clients (./askr/clients/)
    → IDE (./askr/ide/)
    → Hooks (./askr/hooks/)
    → Notifications (./askr/notifications/)
```

Session is the orchestrator; it reads/writes state, calls LLM clients, triggers hooks, and coordinates IDE operations.

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — Client response format changes propagate to session and IDE modules
- **`./askr/utils/`** — Utility function signatures affect all dependent modules
- **`./askr/hooks/`** — Hook event contracts affect session and all hook consumers
