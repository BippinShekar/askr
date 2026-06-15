# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:13 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage, and integrates with IDE/notification systems.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI commands.

## Core Modules

### Session Management (`./askr/session/`)
- `usage_api.py` — Orchestrates session lifecycle, invokes CLI commands, manages platform-specific subprocess execution
- Coordinates with state and client modules to maintain session context

### CLI (`./askr/cli/`)
- Command parsing and routing
- User-facing interface; called by `usage_api.py`

### State Management (`./askr/state/`)
- Maintains session state and configuration
- Persisted to `./askr_state/` directory
- Consumed by session, clients, and hooks

### Clients (`./askr/clients/`)
- External service integrations (likely LLM/API clients)
- Called by session to execute AI operations

### Hooks (`./askr/hooks/`)
- Event handlers triggered during session lifecycle
- Integrates with IDE and notification systems

### IDE Integration (`./askr/ide/`)
- IDE-specific adapters and communication
- Called by hooks for editor interactions

### Notifications (`./askr/notifications/`)
- User notification delivery
- Called by hooks and session for status updates

### QA (`./askr/qa/`)
- Quality assurance and validation logic
- Likely validates AI outputs before delivery

### Utilities (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state directory
- **`./.llm_snapshot/`** — LLM context/snapshot storage
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **Subprocess execution** — Platform-aware command invocation (Windows/Unix)
- **IDE communication** — Via `./askr/ide/`
- **Notification systems** — Via `./askr/notifications/`
- **LLM clients** — Via `./askr/clients/`

## Key Call Chains
```
usage_api.py (entry)
  → cli/ (parse commands)
  → state/ (load/save context)
  → clients/ (execute AI operations)
  → qa/ (validate results)
  → hooks/ (trigger events)
    → ide/ (editor updates)
    → notifications/ (user alerts)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect all modules reading session context
- **`./askr/clients/`** — Client API changes affect session orchestration and QA validation
- **`./askr/hooks/`** — Hook signatures affect IDE and notification integrations
