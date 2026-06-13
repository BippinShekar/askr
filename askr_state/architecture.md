# Architecture

*Auto-generated at checkpoint — 2026-06-13 18:25 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles request/response formatting for different AI backends

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions and file operations
- Manages code context and editor-specific protocols

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**QA/Testing** (`./askr/qa/`)
- Quality assurance and validation logic for agent outputs

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle and state changes

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON or similar format)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation history
- **`./.claude/`** — Claude-specific configuration or credentials

## External Integrations
- **LLM APIs** — Accessed via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — System command invocation via Python `subprocess` module
- **IDE/Editor protocols** — Handled by `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (code context)
  ├→ hooks/ (event callbacks)
  ├→ notifications/ (user feedback)
  └→ utils/ (shared helpers)
```

## Shared Interfaces (High Impact)
- **State schema** (`./askr/state/`) — Changes affect session recovery and persistence across all modules
- **Client protocol** (`./askr/clients/`) — Changes cascade to CLI, session, and QA modules
- **Hook signatures** (`./askr/hooks/`) — Changes affect all event subscribers
- **Utility functions** (`./askr/utils/`) — Used across all modules; breaking changes propagate widely
