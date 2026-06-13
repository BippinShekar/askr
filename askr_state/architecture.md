# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:45 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and IDE/notification hooks.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- **CLI commands** — `./askr/cli/` modules expose user-facing commands that trigger session workflows

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session execution, subprocess management, platform-specific behavior
- Manages session state lifecycle and persistence

**State Management** (`./askr/state/`)
- Maintains in-memory and persisted state (`./askr_state/` directory)
- Tracks conversation history, context, and agent decisions

**Client Integrations** (`./askr/clients/`)
- LLM client implementations (API communication, request/response handling)
- Abstracts different AI model providers

**IDE & Notifications** (`./askr/ide/` and `./askr/notifications/`)
- IDE hooks for editor integration (likely VSCode/Cursor)
- Notification delivery system for user feedback

**QA & Validation** (`./askr/qa/`)
- Code quality checks, test execution, validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions, logging, formatting

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events

## Data Stores
- **`./askr_state/`** — Persistent session state (JSON/serialized format)
- **In-memory state** — Managed by `./askr/state/` during execution

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — Platform-specific command invocation
- **IDE communication** — Through `./askr/ide/` hooks
- **Notification systems** — Via `./askr/notifications/`

## Key Call Chains
```
usage_api.py (entry)
  → session/ (orchestration)
    → state/ (load/persist context)
    → clients/ (LLM requests)
    → qa/ (validation)
    → ide/ + notifications/ (feedback)
    → hooks/ (lifecycle events)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session persistence, clients, and hooks
- **`./askr/clients/`** — LLM response format changes cascade to session logic and QA
- **`./askr/session/usage_api.py`** — Core orchestration; changes affect all workflows
- **`./askr_state/`** — Serialization format changes break session recovery

## Testing & Debugging
- **`./stress-tests/`** — Load/stress test suite
- **`./.llm_snapshot/`** — Cached LLM responses for reproducible testing
- **`./.claude/`** — Claude-specific configuration/context
