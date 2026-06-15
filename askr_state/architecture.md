# Architecture

*Auto-generated at checkpoint — 2026-06-15 11:08 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Main orchestrator; manages session state, subprocess execution, platform detection
- Coordinates with state, clients, and hooks

**State Management** (`./askr/state/`)
- Persists session data to `./askr_state/` directory
- Tracks conversation history, user context, and execution state
- Loaded/saved by `usage_api.py` on session start/end

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider support)
- Called by session layer to fetch AI responses
- Returns structured completions for IDE/CLI consumption

**IDE Integration** (`./askr/ide/`)
- Bridges between Askr and code editors
- Handles code context extraction and insertion
- Communicates with clients for code-aware completions

**Hooks** (`./askr/hooks/`)
- Event-driven handlers for session lifecycle (pre/post execution)
- Triggered by `usage_api.py` at key checkpoints

**Notifications** (`./askr/notifications/`)
- Async notification delivery (session updates, errors)
- Decoupled from main execution flow

**QA** (`./askr/qa/`)
- Validation and testing utilities
- Likely used in stress-tests (`./stress-tests/`)

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, file I/O)
- Used across all modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/pickle format)
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (Claude, OpenAI, or similar)
- **Subprocess Execution** — OS-level command execution (platform-aware via `platform` module)
- **IDE/Editor APIs** — Via `./askr/ide/` module

## Key Relationships
```
usage_api.py (orchestrator)
  ├→ state/ (load/save session)
  ├→ clients/ (fetch AI responses)
  ├→ ide/ (code context + insertion)
  ├→ hooks/ (lifecycle events)
  ├→ notifications/ (async updates)
  └→ subprocess (execute commands)

cli/ → usage_api.py (command routing)
qa/ → all modules (validation)
utils/ → all modules (shared helpers)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Session schema changes affect persistence across all modules
- **`./askr/clients/`** — Response format changes break IDE and CLI consumers
- **`./askr/utils/`** — Logging/formatting changes propagate system-wide
- **`./askr/session/usage_api.py`** — Core API contract; changes affect CLI and all integrations
