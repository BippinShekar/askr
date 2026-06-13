# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:28 UTC*

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
- Handles state serialization/deserialization for session continuity

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple client implementations)
- Handles API calls and response parsing

**IDE Integration** (`./askr/ide/`)
- Bridges between CLI and IDE environments
- Manages code context and file operations

**Notifications** (`./askr/notifications/`)
- Handles user alerts and status updates across channels

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers (pre/post execution, state changes)

**QA Module** (`./askr/qa/`)
- Validation and testing utilities for agent outputs

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — LLM interaction history/snapshots
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar)
- **Subprocess execution** — System command invocation for code execution
- **IDE protocols** — Integration with development environments

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ ide/ (code context)
  ├→ hooks/ (event handling)
  └→ notifications/ (user feedback)

cli/ → session/ → state/ + clients/ + ide/
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence across all modules
- **`./askr/clients/`** — LLM response format changes propagate to session, hooks, and QA
- **`./askr/utils/`** — Utility function signatures impact all dependent modules
- **`./askr/hooks/`** — Event contract changes affect session lifecycle across all services

## Configuration
- Environment detection via `platform` module in `usage_api.py`
- State directory: `./askr_state/`
