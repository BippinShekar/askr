# Architecture

*Auto-generated at checkpoint — 2026-06-15 16:49 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and IDE/notification hooks.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- `./askr/cli/` — Command-line interface handlers that dispatch to session management

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Main orchestrator; spawns processes, manages session state transitions
- Coordinates between CLI input, state persistence, and client execution

**State Management** (`./askr/state/`)
- Maintains session state across invocations
- Persisted to `./askr_state/` directory
- Consumed by session and client modules

**Client Layer** (`./askr/clients/`)
- LLM client implementations (likely OpenAI, Anthropic, or similar)
- Handles API communication and response parsing
- Called by session layer during execution

**IDE Integration** (`./askr/ide/`)
- Editor hooks and file manipulation
- Receives file paths and diffs from session layer
- Applies code changes to workspace

**Notifications** (`./askr/notifications/`)
- Status/result delivery (likely Slack, email, or terminal output)
- Triggered by session state changes

**QA/Validation** (`./askr/qa/`)
- Test execution and result validation
- Called post-execution to verify changes

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, path resolution)
- Used across all modules

**Hooks** (`./askr/hooks/`)
- Pre/post-execution lifecycle callbacks
- Extensibility points for custom integrations

## Data Stores
- `./askr_state/` — Session state persistence (JSON or similar)
- `./Formula/` — Likely template/configuration definitions
- `./.llm_snapshot/` — Cached LLM responses or context snapshots

## External Integrations
- LLM APIs (via `clients/`)
- IDE/editor (via `ide/`)
- Notification services (via `notifications/`)
- Subprocess execution (platform-dependent via `usage_api.py`)

## Key Call Flow
```
CLI → session/usage_api.py → state/ (load/save)
                           → clients/ (LLM calls)
                           → ide/ (apply changes)
                           → qa/ (validate)
                           → notifications/ (report)
                           → hooks/ (callbacks)
```

## Shared Interfaces (High-Impact Changes)
- `./askr/state/` — Any schema changes affect session persistence and all consumers
- `./askr/clients/` — Response format changes break session parsing and IDE integration
- `./askr/utils/` — Utility modifications propagate across all modules
- `./askr_state/` directory structure — Affects state loading in session and CLI
