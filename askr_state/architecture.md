# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:36 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles notifications, and integrates with IDEs for code analysis and generation.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; manages session lifecycle, platform detection, and subprocess orchestration
- **CLI commands** — `./askr/cli/` module provides command-line interface for user interactions

## Core Modules

**Session Management** (`./askr/session/`)
- Handles session state, lifecycle, and usage tracking
- `usage_api.py` coordinates subprocess execution and platform-specific operations

**State Management** (`./askr/state/`)
- Maintains application state across operations
- Persists to `./askr_state/` directory

**Client Integrations** (`./askr/clients/`)
- Abstracts external service connections (likely LLM providers, code analysis tools)
- Provides unified interface for downstream modules

**IDE Integration** (`./askr/ide/`)
- Bridges IDE-specific functionality (editor detection, file operations, syntax awareness)
- Enables code context passing to AI models

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates
- Decouples notification logic from core business logic

**QA/Testing** (`./askr/qa/`)
- Quality assurance utilities and test helpers

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks (likely git hooks, file watchers, or lifecycle events)

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local state persistence (session data, configuration, cache)
- **In-memory state** — `./askr/state/` module manages runtime state

## External Integrations
- **Subprocess execution** — Platform-aware process management (Windows/Unix)
- **IDE APIs** — Editor integration via `./askr/ide/`
- **External services** — Abstracted through `./askr/clients/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (external services)
  ├→ ide/ (editor context)
  ├→ notifications/ (user feedback)
  ├→ hooks/ (event handling)
  └→ cli/ (command routing)
```

## Shared Interfaces (High Impact)
- **`./askr/clients/`** — Any changes to client abstraction affect all service integrations
- **`./askr/state/`** — State schema changes propagate to session, hooks, and persistence
- **`./askr/utils/`** — Utility modifications impact all dependent modules
- **`./askr/session/usage_api.py`** — Core orchestration; changes affect entire execution flow
