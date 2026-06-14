# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:31 UTC*

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
- Maintains session state and persistence
- Syncs with `./askr_state/` directory for file-based storage

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely OpenAI, Anthropic, etc.)
- Manages API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE interaction layer
- Handles file operations and syntax awareness

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle (pre/post execution)
- Extensibility points for custom behaviors

**Notifications** (`./askr/notifications/`)
- User alerts and status updates
- Likely integrates with system notifications or logging

**QA Module** (`./askr/qa/`)
- Code quality checks and validation
- Test execution or linting integration

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — File-based session state persistence (JSON or similar)
- **In-memory state** — Runtime session data via `./askr/state/`

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (subprocess calls to external services)
- **System subprocess** — Platform-specific execution via `os.subprocess`
- **IDE/Editor APIs** — Via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ cli/ (input parsing)
  ├→ clients/ (LLM communication)
  ├→ hooks/ (event callbacks)
  ├→ ide/ (file/editor ops)
  ├→ notifications/ (user feedback)
  └→ qa/ (validation)
```

## Shared Interfaces
- **`./askr/state/`** — State schema changes affect session persistence, CLI output, and client context
- **`./askr/clients/`** — API response format changes impact all modules consuming LLM outputs
- **`./askr/hooks/`** — Hook signatures affect all modules registering callbacks
- **`./askr_state/` directory structure** — File layout changes break state loading across all modules
