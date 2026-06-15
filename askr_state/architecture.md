# Architecture

*Auto-generated at checkpoint — 2026-06-15 11:03 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session state, subprocess execution, and platform detection
- Manages session lifecycle and coordinates between CLI and backend services

**State Management** (`./askr/state/`)
- Persists and retrieves session state (likely JSON-based in `./askr_state/`)
- Maintains conversation history and user context across invocations

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (API communication, request/response handling)
- Abstracts different AI model providers

**IDE Integration** (`./askr/ide/`)
- Code editor hooks and file manipulation
- Bridges between LLM suggestions and local development environment

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Likely integrates with system notifications or CLI output

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)
- Integration points for extensibility

**QA** (`./askr/qa/`)
- Testing and validation logic
- Likely validates LLM outputs or code suggestions

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Local session state storage (JSON or similar)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation snapshots
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (likely OpenAI, Anthropic, or similar)
- **Subprocess execution** — System commands via Python `subprocess` module
- **File system** — IDE integration reads/writes code files

## Key Relationships
```
CLI (./askr/cli/) 
  → usage_api.py (session orchestration)
    → clients/ (LLM requests)
    → state/ (persistence)
    → ide/ (code manipulation)
    → notifications/ (user feedback)
    → hooks/ (event handling)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any schema changes affect session persistence across all modules
- **`./askr/clients/`** — LLM response format changes propagate to IDE, QA, and hooks
- **`./askr/utils/`** — Shared utilities; changes affect all dependent modules
- **`./askr/session/usage_api.py`** — Central orchestrator; changes impact entire execution flow
