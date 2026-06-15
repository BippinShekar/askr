# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:41 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to session handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session execution, subprocess spawning, environment setup
- Manages session state lifecycle and cleanup

**State Management** (`./askr/state/`)
- Persists and retrieves session state (likely JSON/file-based in `./askr_state/`)
- Tracks conversation history, context, and user preferences

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (OpenAI, Anthropic, etc.)
- Manages API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, editor integration hooks
- Bridges between LLM responses and local development environment

**Notifications** (`./askr/notifications/`)
- Async event delivery (completion alerts, errors, status updates)
- Decouples session logic from user feedback mechanisms

**Hooks** (`./askr/hooks/`)
- Pre/post-execution callbacks for extensibility
- Integrates with IDE and notification systems

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework
- Verifies LLM-generated code

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (file-based)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation snapshots
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **LLM APIs** — Routed through `./askr/clients/`
- **Subprocess execution** — Via `usage_api.py` for code execution
- **File system** — Through `./askr/ide/` for code reading/writing
- **Platform-specific tools** — Abstracted in `usage_api.py` (subprocess, os, platform modules)

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) + Clients (./askr/clients/)
    → IDE (./askr/ide/) + Hooks (./askr/hooks/)
    → QA (./askr/qa/) + Notifications (./askr/notifications/)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence and all consumers
- **`./askr/clients/`** — LLM response format changes propagate to IDE, QA, and hooks
- **`./askr/utils/`** — Shared validation/formatting utilities used across all modules
- **`./askr/hooks/`** — Hook signatures affect IDE, notifications, and session flow

## Development Notes
- Subprocess isolation in `usage_api.py` suggests sandboxed code execution
- State-driven architecture enables resumable sessions
- Hook system enables plugin-like extensibility without core modifications
