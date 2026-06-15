# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:36 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution entry point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers triggered by user input

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, platform detection
- Manages active session state and execution context

**State Management** (`./askr/state/`)
- Persistent state storage and retrieval
- Coordinates with `./askr_state/` directory for state artifacts

**Client Integrations** (`./askr/clients/`)
- LLM client implementations (likely multiple provider support)
- Request/response handling for external AI services

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE communication layer
- File operations and workspace context

**Notifications** (`./askr/notifications/`)
- Event-driven alerts and status updates
- User feedback mechanisms

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers (pre/post execution)
- Integration points for extensibility

**QA/Testing** (`./askr/qa/`)
- Test execution and validation
- Code quality checks

**Utilities** (`./askr/utils/`)
- Shared helper functions
- Common operations across modules

## Data Stores
- **`./askr_state/`** — Session state persistence (likely JSON/YAML files)
- **`./.llm_snapshot/`** — LLM interaction snapshots/history
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (Claude, other providers)
- **Subprocess execution** — System commands via Python subprocess module
- **IDE/Editor APIs** — Through `./askr/ide/` layer

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (workspace context)
  ├→ hooks/ (event handling)
  └→ notifications/ (user feedback)

cli/ (user commands)
  └→ session/ (execution)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Client interface changes impact all LLM-dependent modules (session, hooks, qa)
- **`./askr/utils/`** — Utility function signatures affect all consumers
- **`./askr_state/` directory** — State file format changes break session compatibility

## Critical Constraints
- Session state must remain serializable for persistence
- Client implementations must support async/subprocess execution patterns
- IDE integration must handle concurrent file operations
