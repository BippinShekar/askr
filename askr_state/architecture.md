# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:02 UTC*

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

**Client Handlers** (`./askr/clients/`)
- Abstracts multiple LLM client implementations (likely OpenAI, Anthropic, etc.)
- Handles API communication and response parsing

**State Management** (`./askr/state/`)
- Persists session state to `./askr_state/` directory
- Tracks conversation history, file modifications, and execution context

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor interactions
- Bridges between agent decisions and actual file modifications

**Notifications** (`./askr/notifications/`)
- User feedback delivery (console, webhooks, or external services)

**QA/Validation** (`./askr/qa/`)
- Test execution, output validation, and error checking

**Hooks** (`./askr/hooks/`)
- Pre/post-execution callbacks for extensibility

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction snapshots for debugging/replay
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Routed through `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — Platform-aware shell commands via `usage_api.py`
- **File system** — Read/write operations through `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init)
  ├→ cli/ (command parse)
  ├→ clients/ (LLM calls)
  ├→ state/ (persistence)
  ├→ ide/ (file ops)
  ├→ qa/ (validation)
  ├→ notifications/ (feedback)
  └→ hooks/ (callbacks)
```

## Shared Interfaces
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — Response format changes impact CLI, QA, and IDE modules
- **`./askr/utils/`** — Utility function signatures affect all consumers
- **`./askr_state/` directory structure** — Affects state loading in `session/` and recovery logic
