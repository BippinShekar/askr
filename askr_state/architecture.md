# Architecture

*Auto-generated at checkpoint — 2026-06-15 21:33 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles user queries, and integrates with external AI clients for code analysis and generation.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, spawns subprocesses, and manages platform-specific operations

## Core Modules

### Session Management (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform detection
- Manages user session state and lifecycle

### CLI (`./askr/cli/`)
- Command-line interface and argument parsing
- Routes user input to appropriate handlers

### State Management (`./askr/state/`)
- Maintains application state across operations
- Persists to `./askr_state/` directory

### Client Integrations (`./askr/clients/`)
- Abstractions for external AI/LLM services
- Handles API communication and response parsing

### IDE Integration (`./askr/ide/`)
- Code editor/IDE interaction layer
- File operations and workspace awareness

### Notifications (`./askr/notifications/`)
- User-facing alerts and status updates
- Async notification delivery

### QA Module (`./askr/qa/`)
- Quality assurance and validation logic
- Test execution and result verification

### Hooks (`./askr/hooks/`)
- Event-driven callbacks and lifecycle hooks
- Integration points for extensibility

### Utilities (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Local session state persistence
- **`./.llm_snapshot/`** — LLM interaction snapshots/cache
- **`./.claude/`** — Claude-specific configuration/context

## External Integrations
- **AI Clients** — LLM APIs via `./askr/clients/`
- **Subprocess execution** — OS-level command invocation
- **File system** — Code workspace access via `./askr/ide/`

## Key Call Relationships
```
usage_api.py (entry)
  ├→ cli/ (parse commands)
  ├→ session/ (manage lifecycle)
  ├→ state/ (read/write state)
  ├→ clients/ (query AI services)
  ├→ ide/ (interact with code)
  ├→ qa/ (validate results)
  └→ notifications/ (alert user)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect all modules reading session data
- **`./askr/clients/`** — Client response formats consumed by `session/`, `qa/`, `ide/`
- **`./askr/utils/`** — Utility function signatures used across all modules
- **`./.llm_snapshot/`** — Cache format affects reproducibility and debugging

## Testing
- `./tests/` — Unit and integration tests
- `./stress-tests/` — Performance and load testing
