# Architecture

*Auto-generated at checkpoint — 2026-06-14 09:14 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding assistant that manages user sessions, tracks usage, and integrates with IDE environments and external AI clients.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session usage tracking via subprocess calls and platform detection
- **CLI commands** — `./askr/cli/` directory contains command handlers triggered by user input

## Core Modules

### Session Management (`./askr/session/`)
- `usage_api.py` — Tracks and reports usage metrics; spawns subprocesses for background operations
- Manages user session state and lifecycle

### State Management (`./askr/state/`)
- Maintains application state persistence
- Interfaces with `./askr_state/` directory for state storage

### Client Integrations (`./askr/clients/`)
- Abstractions for external AI/LLM providers
- Multiple client implementations for different services

### IDE Integration (`./askr/ide/`)
- IDE-specific hooks and communication
- Bridges between Askr core and editor environments

### Notifications (`./askr/notifications/`)
- User-facing alerts and status updates
- Decoupled from core logic

### Utilities (`./askr/utils/`)
- Shared helper functions across modules
- Logging, formatting, common operations

### QA & Testing (`./askr/qa/`)
- Test utilities and validation logic

### Hooks (`./askr/hooks/`)
- Event-driven integrations
- Lifecycle callbacks for plugins/extensions

## Data Stores
- **`./askr_state/`** — Persistent state storage (session data, configuration, cache)
- **`./Formula/`** — Likely formula/template definitions or cached responses

## External Integrations
- **LLM Clients** — Multiple AI provider integrations via `./askr/clients/`
- **IDE Plugins** — Communication via `./askr/ide/`
- **System Subprocess** — `usage_api.py` spawns background processes for async operations

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/ + ./askr_state/)
    → Clients (./askr/clients/)
    → IDE (./askr/ide/)
    → Notifications (./askr/notifications/)
    → Hooks (./askr/hooks/)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session, clients, and IDE modules
- **`./askr/clients/`** — Client interface changes propagate to CLI and session handlers
- **`./askr/utils/`** — Utility function signatures used across all modules
- **`./askr_state/`** — Storage format changes break session persistence

## Testing & Stress
- `./stress-tests/` — Load/performance testing suite
- `./askr/qa/` — Quality assurance utilities
