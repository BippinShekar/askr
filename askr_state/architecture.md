# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:43 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment context
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history and execution context

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Translates between internal message format and external API contracts

**CLI Interface** (`./askr/cli/`)
- Command parsing and routing
- User input validation and formatting

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor communication
- Bridges between agent logic and development environment

**Notifications** (`./askr/notifications/`)
- Event publishing for session state changes
- Async notification delivery

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework
- Likely used for agent self-verification

**Hooks** (`./askr/hooks/`)
- Lifecycle callbacks (pre/post execution, state transitions)

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local filesystem storage for session state, conversation history, and execution artifacts
- **Environment variables** — Configuration via `os.environ` (platform detection, API keys)

## External Integrations
- **LLM APIs** — Abstracted through `./askr/clients/`; subprocess execution suggests potential remote agent calls
- **Subprocess execution** — `subprocess` module in `usage_api.py` for running external tools/scripts
- **File system** — IDE module reads/writes code files

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init & tracking)
  ├→ state/ (persistence layer)
  ├→ clients/ (LLM communication)
  ├→ cli/ (command dispatch)
  ├→ ide/ (file operations)
  ├→ notifications/ (event bus)
  └→ hooks/ (lifecycle callbacks)

cli/ → session/ → state/ + clients/
ide/ ← session/ (file context)
qa/ ← clients/ (validation)
```

## Shared Interfaces
- **`./askr/state/`** — Any state schema changes affect session initialization, persistence, and client context building
- **`./askr/clients/`** — Message format changes propagate to CLI, session, and IDE modules
- **`./askr/utils/`** — Utility function signatures impact all dependent modules
- **`./askr_state/` directory structure** — Schema changes require migration logic in session module
