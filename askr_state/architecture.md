# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:08 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment context
- **CLI commands** — `./askr/cli/` modules expose user-facing commands that trigger session workflows

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session lifecycle, subprocess orchestration, environment detection
- Manages active session state and coordinates between CLI and backend services

**State Management** (`./askr/state/`)
- Persistent session state storage and retrieval
- Interfaces with `./askr_state/` directory for state artifacts

**Client Integrations** (`./askr/clients/`)
- LLM client implementations (API communication, request/response handling)
- Multiple client types for different AI providers

**IDE Integration** (`./askr/ide/`)
- Code editor hooks and file manipulation
- Bridges between AI suggestions and local development environment

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates
- Decoupled from core logic

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)
- Integration points for extensibility

**QA/Testing** (`./askr/qa/`)
- Validation and testing utilities
- Code quality checks before execution

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON/structured data)
- **`./.llm_snapshot/`** — LLM interaction history and context snapshots
- **`./.claude/`** — Agent-specific configuration and metadata

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Claude, or similar)
- **Subprocess execution** — System commands via Python `subprocess` module
- **IDE/Editor APIs** — File system and editor protocol via `./askr/ide/`

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (code changes)
  ├→ hooks/ (event dispatch)
  ├→ notifications/ (user feedback)
  └→ utils/ (shared utilities)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session recovery and persistence across all modules
- **`./askr/clients/`** — LLM request/response contracts used by session and hooks
- **`./askr/utils/`** — Logging, config parsing, file I/O used everywhere
- **`./askr/session/usage_api.py`** — Central orchestrator; changes propagate to CLI and all downstream services

## Testing & Validation
- `./stress-tests/` — Load and integration tests
- `./askr/qa/` — Pre-execution validation
