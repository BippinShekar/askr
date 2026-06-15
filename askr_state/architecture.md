# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:43 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics, and orchestrates subprocess execution for development workflows.

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates session creation and subprocess invocation

**CLI Interface** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate handlers

**Client Handlers** (`./askr/clients/`)
- Abstracts multiple LLM client implementations
- Manages API communication and response parsing

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/`
- Tracks conversation history, context, and execution results

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor interactions
- Bridges between agent logic and development environment

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates

**QA Module** (`./askr/qa/`)
- Validation and testing utilities for generated code

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/structured format)
- **Environment variables** — Configuration (platform detection via `platform` module)
- **Subprocess outputs** — Captured from executed commands

## External Integrations
- **LLM APIs** — Abstracted via `./askr/clients/`; supports multiple providers
- **System subprocess** — Executes development commands; output captured and logged
- **File system** — Read/write via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence to ./askr_state/)
  ├→ cli/ (command parsing)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file operations)
  ├→ hooks/ (event callbacks)
  └→ notifications/ (user feedback)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Client abstraction layer; changes to response format impact CLI, IDE, and QA modules
- **`./askr/utils/`** — Shared utilities; breaking changes propagate across all modules
- **`./askr/hooks/`** — Event contract; new/removed hooks affect session lifecycle coordination

## Configuration
- Platform detection (`platform` module) for OS-specific behavior
- Subprocess execution with JSON output parsing for structured results
