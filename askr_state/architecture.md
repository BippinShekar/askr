# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:20 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages development sessions, handles user interactions, and tracks usage metrics.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; initializes session tracking and usage reporting via subprocess calls and platform detection

## Core Modules

**CLI Layer** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate service handlers

**Session Management** (`./askr/session/`)
- `usage_api.py` — Tracks and reports usage metrics; spawns subprocess for telemetry
- Session lifecycle: creation, state persistence, cleanup

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Persists to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- External service communication (likely LLM APIs, version control)
- Abstracts provider-specific logic

**IDE Integration** (`./askr/ide/`)
- Editor/IDE communication and file operations
- Workspace context management

**Supporting Services**
- `./askr/hooks/` — Event handlers and lifecycle callbacks
- `./askr/notifications/` — User notifications and alerts
- `./askr/qa/` — Quality assurance and validation logic
- `./askr/utils/` — Shared utilities (logging, helpers)

## Data Stores
- `./askr_state/` — Local state persistence (session data, configuration)
- `./Formula/` — Likely template or formula definitions for code generation

## External Integrations
- Subprocess execution (platform-aware command invocation)
- IDE/editor APIs (via `./askr/ide/`)
- External services (via `./askr/clients/`)

## Key Relationships
```
CLI → Session (usage_api.py)
    ↓
State Management (./askr_state/)
    ↓
Clients (external services)
    ↓
IDE Integration (file operations)
    ↓
Notifications/Hooks (side effects)
```

Entry point `usage_api.py` orchestrates session initialization → state retrieval → client calls → IDE updates → notification dispatch.

## Shared Interfaces (High Impact)
- `./askr/state/` — Any state schema changes affect all modules reading/writing state
- `./askr/clients/` — Client interface changes propagate to CLI, session, and IDE layers
- `./askr/utils/` — Utility function signatures impact all consumers

## Testing & Stress
- `./stress-tests/` — Load/performance testing suite
- `./askr/qa/` — Validation and test utilities
