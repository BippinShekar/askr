# Architecture

*Auto-generated at checkpoint — 2026-06-15 22:26 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles notifications, and integrates with IDEs for code analysis and generation.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, spawns subprocesses, and collects platform/environment data
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session and state management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session execution, subprocess management, platform detection
- Manages session state persistence and lifecycle

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Persists to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- Abstracts external API clients (LLM providers, code analysis services)
- Handles authentication and request/response formatting

**IDE Integration** (`./askr/ide/`)
- Bridges IDE communication (likely LSP or plugin protocol)
- Translates between IDE events and internal representations

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decouples notification logic from core services

**QA/Testing** (`./askr/qa/`)
- Test utilities and validation logic
- Likely used by stress tests in `./stress-tests/`

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, file I/O)

**Hooks** (`./askr/hooks/`)
- Event handlers for lifecycle events (pre/post execution)

## Data Stores
- **`./askr_state/`** — Local state persistence (session data, configuration)
- **`./Formula/`** — Likely template or formula definitions for code generation

## External Integrations
- Subprocess execution (Python's `subprocess` module)
- Platform detection (`platform` module)
- File system operations (`os` module)
- JSON serialization for state/API communication

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (external APIs)
  ├→ ide/ (IDE communication)
  ├→ notifications/ (user feedback)
  └→ hooks/ (event handling)

cli/ → session/ → state/
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all consumers
- **`./askr/clients/`** — Client interface changes propagate to session, IDE, and CLI
- **`./askr/utils/`** — Utility function signatures used across all modules
- **`./askr/hooks/`** — Hook contract changes affect session lifecycle and IDE integration

## Testing
- `./tests/` — Unit and integration tests
- `./stress-tests/` — Load/performance testing against session and client layers
