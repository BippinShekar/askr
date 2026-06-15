# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:22 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Handles state serialization/deserialization for session recovery

**Client Integrations** (`./askr/clients/`)
- LLM client adapters (likely OpenAI, Anthropic, or similar)
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE interaction layer
- File operations and syntax awareness

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Likely integrates with system notifications or terminal output

**QA/Testing** (`./askr/qa/`)
- Test execution and validation framework
- Verifies code changes before committing

**Hooks** (`./askr/hooks/`)
- Git/VCS integration points
- Pre/post-execution lifecycle hooks

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON or similar format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Integrated via `./askr/clients/`
- **Subprocess execution** — System command invocation via `usage_api.py`
- **Git/VCS** — Hooked via `./askr/hooks/`
- **IDE/Editor** — Interfaced through `./askr/ide/`

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/) → ./askr_state/
    → Clients (./askr/clients/) → LLM APIs
    → IDE (./askr/ide/) → File system
    → QA (./askr/qa/) → Test execution
    → Hooks (./askr/hooks/) → Git
    → Notifications (./askr/notifications/) → User output
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — LLM response format changes cascade to all consumers (CLI, QA, IDE)
- **`./askr/utils/`** — Shared utilities used across all modules; breaking changes here affect entire system
- **`./askr/session/usage_api.py`** — Core orchestration; changes affect CLI routing and subprocess handling
