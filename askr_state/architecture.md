# Architecture

*Auto-generated at checkpoint — 2026-06-14 09:05 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely multiple AI backends)
- Translates between internal message formats and provider APIs

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file system operations
- Enables in-editor code suggestions and modifications

**Notifications** (`./askr/notifications/`)
- Delivers session events and results to users
- Likely supports multiple notification channels

**QA/Testing** (`./askr/qa/`)
- Validation and testing utilities for session outputs

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar)
- **Environment variables** — Configuration via `os.environ` (platform detection, API keys)

## External Integrations
- **Subprocess execution** — Runs code/commands via `subprocess` module
- **LLM providers** — Abstracted through `./askr/clients/`
- **IDE/Editor** — File system and editor protocol integration via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state management)
  ├→ clients/ (LLM communication)
  ├→ state/ (persistence)
  ├→ hooks/ (event dispatch)
  ├→ notifications/ (output)
  └→ ide/ (editor integration)

cli/ (user commands)
  └→ session/ + clients/ + state/
```

## Shared Interfaces (High Impact)
- **`./askr/session/`** — Session object contract; changes affect all modules
- **`./askr/state/`** — State schema; changes break session recovery
- **`./askr/clients/`** — LLM message format; changes require updates across session + hooks
- **`./askr/utils/`** — Utility signatures; widely imported

## Configuration
- Platform detection via `platform` module
- Subprocess environment inherited from parent process
- State directory: `./askr_state/`
