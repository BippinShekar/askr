# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:32 UTC*

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

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Abstracts API communication and response handling

**IDE Integration** (`./askr/ide/`)
- Editor/IDE interaction layer
- Likely handles file operations, syntax awareness, and editor-specific commands

**Notifications** (`./askr/notifications/`)
- Async notification delivery (email, webhooks, or in-app alerts)
- Decoupled from core session logic

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework
- Likely runs generated code or validates AI outputs

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks (pre/post session, on state changes)
- Extensibility mechanism for custom workflows

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation history
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **LLM APIs** — Called via `./askr/clients/`
- **Subprocess execution** — OS-level code execution via `subprocess` module
- **IDE/Editor APIs** — Integrated through `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (editor interaction)
  ├→ hooks/ (event callbacks)
  ├→ notifications/ (async alerts)
  └→ qa/ (validation)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — LLM response format changes propagate to session, hooks, and QA
- **`./askr/utils/`** — Shared utilities; breaking changes affect all consumers
- **`./askr/hooks/`** — Event signatures; changes break all hook implementations
