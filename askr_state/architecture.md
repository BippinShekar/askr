# Architecture

*Auto-generated at checkpoint — 2026-06-13 15:51 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` module provides command-line interface handlers

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization across invocations

**Client Handlers** (`./askr/clients/`)
- Abstracts multiple LLM client implementations (likely OpenAI, Anthropic, etc.)
- Normalizes API calls across different providers

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file operations
- Manages workspace context and file state

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates

**QA/Validation** (`./askr/qa/`)
- Code quality checks and validation logic

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state directory (JSON-based)
- **`./.llm_snapshot/`** — LLM interaction snapshots/logs
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **Subprocess execution** — Runs code/commands via `subprocess` module
- **LLM APIs** — Multiple client implementations in `./askr/clients/`
- **Platform detection** — Uses `platform` module for OS-specific behavior

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (workspace context)
  ├→ hooks/ (event handlers)
  └→ subprocess (code execution)

cli/ → session/ → state/ + clients/
notifications/ ← session/ (status updates)
qa/ ← ide/ (validation on file changes)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/session/`** — Session contract used by CLI, usage_api, and hooks; changes affect all entry points
- **`./askr/state/`** — State schema; changes break persistence compatibility across versions
- **`./askr/clients/`** — Client abstraction; changes affect all LLM integrations
- **`./askr/ide/`** — Workspace context interface; changes affect QA and hooks

## Configuration
- Environment variables likely read in `usage_api.py` and client modules
- State directory: `./askr_state/`
