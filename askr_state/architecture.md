# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:48 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and IDE/notification hooks.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Main orchestrator; spawns subprocess workflows, handles platform-specific execution
- Manages session lifecycle and state transitions

**State Management** (`./askr/state/`)
- Persists and retrieves session state (likely JSON-based given `json` import in usage_api)
- Shared state store at `./askr_state/` (directory-level persistence)

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (OpenAI, Claude, etc.)
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Editor hooks and file manipulation
- Bridges between LLM suggestions and code changes

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Likely integrates with system notifications or CLI output

**QA/Validation** (`./askr/qa/`)
- Test execution and result validation
- Verifies LLM-generated code changes

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

**Hooks** (`./askr/hooks/`)
- Event listeners for IDE/file system changes
- Triggers session updates on external events

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON or similar)
- **`./.llm_snapshot/`** — LLM conversation history/snapshots
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- LLM APIs (via `./askr/clients/`)
- IDE/editor (via `./askr/ide/`)
- System notifications (via `./askr/notifications/`)
- Subprocess execution (platform-dependent via `usage_api.py`)

## Key Call Chain
```
usage_api.py (entry)
  → session management
    → state (read/write)
    → clients (LLM queries)
    → ide (apply changes)
    → qa (validate)
    → notifications (feedback)
    → hooks (listen for changes)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — LLM response format changes cascade to ide, qa, and session modules
- **`./askr/session/usage_api.py`** — Core subprocess/platform logic; changes affect all execution paths
