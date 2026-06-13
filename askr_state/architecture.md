# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:33 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with context-aware code analysis and user notifications.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; orchestrates session lifecycle via subprocess calls and platform-specific operations
- `./askr/cli/` — Command-line interface layer that routes user input to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session execution, handles subprocess spawning and OS-level interactions
- Manages session state persistence and lifecycle

**State Management** (`./askr/state/`)
- Maintains application state across execution contexts
- Shared state store referenced by multiple subsystems

**Client Integrations** (`./askr/clients/`)
- Abstracts external API clients (likely LLM providers, code analysis tools)
- Decouples service implementations from core logic

**IDE Integration** (`./askr/ide/`)
- Handles editor/IDE communication and code context extraction
- Bridges between development environment and agent logic

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decoupled from core logic for extensibility

**QA/Testing** (`./askr/qa/`)
- Validation and quality assurance logic
- Likely includes test execution and result verification

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for lifecycle events
- Enables plugin-like extensibility

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- `./askr_state/` — Persistent session state directory
- `./.llm_snapshot/` — Cached LLM context/snapshots
- `./.claude/` — Agent-specific configuration/cache

## External Integrations
- Subprocess execution (OS-level code execution)
- Platform-specific operations (via `platform` module)
- LLM clients (abstracted in `./askr/clients/`)

## Key Dependencies
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (shared state)
  ├→ clients/ (external APIs)
  ├→ ide/ (context)
  ├→ notifications/ (output)
  ├→ hooks/ (events)
  └→ qa/ (validation)
```

## Critical Interfaces
- **`./askr/state/`** — Changing state schema affects all consumers (session, clients, qa)
- **`./askr/clients/`** — Client contract changes impact session execution flow
- **`./askr/hooks/`** — Hook signatures affect all event subscribers
- **`./askr/session/usage_api.py`** — Central orchestrator; changes propagate widely

## Modification Impact
- State schema changes → requires updates across session, clients, qa modules
- Client API changes → breaks session orchestration
- Hook signatures → breaks all subscribers in notifications, qa, ide
- CLI changes → affects entry point routing
