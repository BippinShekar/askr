# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:41 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics, and orchestrates subprocess execution across platforms (Linux/macOS/Windows).

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess calls and platform-specific execution

**CLI Interface** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate handlers

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Coordinates with `./askr_state/` directory for state storage

**Client Integrations** (`./askr/clients/`)
- LLM client implementations (API communication, request/response handling)
- Abstracts different AI provider interfaces

**IDE Integration** (`./askr/ide/`)
- Editor/IDE communication and file operations
- Handles code context and file modifications

**Notifications** (`./askr/notifications/`)
- User alerts and status updates
- Integrates with system notification services

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle (pre/post execution)
- Extensibility points for custom behaviors

**QA/Testing** (`./askr/qa/`)
- Test execution and validation
- Code quality checks

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/structured data)
- **Environment variables** — Configuration and credentials (read in `usage_api.py`)

## External Integrations
- **LLM APIs** — Accessed via `./askr/clients/` (request/response handling)
- **System subprocess** — Spawned from `usage_api.py` for code execution
- **File system** — Read/write via `./askr/ide/`
- **System notifications** — Via `./askr/notifications/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ cli/ (input parsing)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file operations)
  ├→ hooks/ (event dispatch)
  └→ notifications/ (user feedback)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — State schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — LLM response format changes cascade to CLI, IDE, and QA modules
- **`./askr/utils/`** — Utility function signatures impact all dependent modules
- **`./askr/hooks/`** — Hook event contracts affect session lifecycle coordination
