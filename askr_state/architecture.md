# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:25 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Main orchestrator; manages session state, subprocess execution, platform detection
- Coordinates between CLI input, state persistence, and client communication

**State Management** (`./askr/state/`)
- Maintains session state across invocations
- Persists to `./askr_state/` directory
- Shared state interface for all components

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider communication
- Multiple client implementations for different AI backends
- Called by session manager to execute AI operations

**IDE Integration** (`./askr/ide/`)
- Bridges code editor/IDE interactions
- Reads/writes code artifacts during sessions

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates
- Decoupled from core session logic

**Hooks** (`./askr/hooks/`)
- Lifecycle callbacks (pre/post session, pre/post execution)
- Extensibility points for custom behaviors

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/structured files)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (OpenAI, Anthropic, etc.)
- **Subprocess Execution** — OS-level command execution via Python `subprocess`
- **IDE/Editor APIs** — Via `./askr/ide/`

## Key Call Chains
```
usage_api.py (entry)
  → session state loader (./askr/state/)
  → CLI router (./askr/cli/)
  → client handler (./askr/clients/)
  → IDE integration (./askr/ide/)
  → hooks (./askr/hooks/)
  → state persistence (./askr_state/)
  → notifications (./askr/notifications/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — All modules depend on state schema; changes break session persistence
- **`./askr/clients/`** — Client interface used by session manager; changes affect all LLM operations
- **`./askr/hooks/`** — Hook signatures used across session lifecycle; changes cascade to all hook consumers
- **`./askr_state/` schema** — Data format consumed by state loader; breaking changes prevent session recovery
