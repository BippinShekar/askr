# Architecture

*Auto-generated at checkpoint — 2026-06-12 15:03 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, tracking usage and state across multiple IDE environments.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks API usage, and manages subprocess execution for IDE integration

## Core Modules

### Session Management (`./askr/session/`)
- `usage_api.py` — Session lifecycle, usage tracking, subprocess orchestration
- Manages state persistence and session metadata

### CLI (`./askr/cli/`)
- Command-line interface layer
- Routes user input to appropriate handlers

### State Management (`./askr/state/`)
- Maintains application state across sessions
- Persists to `./askr_state/` directory

### Client Integrations (`./askr/clients/`)
- LLM client implementations
- Handles API communication with external models

### IDE Integration (`./askr/ide/`)
- IDE-specific adapters and communication protocols
- Bridges between Askr and editor environments

### Notifications (`./askr/notifications/`)
- User-facing alerts and status updates

### QA (`./askr/qa/`)
- Testing and validation utilities

### Hooks (`./askr/hooks/`)
- Lifecycle event handlers (pre/post execution)

### Utilities (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/structured data)
- **Environment variables** — Configuration via `os.environ`
- **Platform detection** — Uses `platform` module for OS-specific behavior

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (model inference)
- **Subprocess execution** — IDE communication and tool invocation
- **System platform** — OS detection for cross-platform compatibility

## Key Relationships
```
usage_api.py (entry)
  ├─> session/ (state management)
  ├─> clients/ (LLM communication)
  ├─> ide/ (IDE adapters)
  ├─> state/ (persistence)
  ├─> cli/ (command routing)
  ├─> hooks/ (event handling)
  ├─> notifications/ (user feedback)
  └─> utils/ (shared helpers)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — LLM response formats consumed by session, hooks, and QA modules
- **`./askr/utils/`** — Utility functions used across all modules; breaking changes cascade widely
- **`./askr/session/usage_api.py`** — Central orchestrator; changes affect CLI routing and subprocess handling

## Configuration
- Platform-aware execution via `platform` module
- Subprocess management for IDE communication
- JSON-based state serialization
