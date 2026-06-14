# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:30 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to session and state managers

## Core Modules

**Session Management** (`./askr/session/`)
- Owns session lifecycle, usage tracking, and API interactions
- `usage_api.py` coordinates subprocess calls and environment detection

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history and user preferences

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely OpenAI, Anthropic, etc.)
- Translates between internal message format and provider APIs

**IDE Integration** (`./askr/ide/`)
- Bridges code editor interactions
- Handles file operations and syntax awareness

**Notifications** (`./askr/notifications/`)
- Delivers async alerts (completion, errors, state changes)

**QA/Validation** (`./askr/qa/`)
- Tests generated code and validates outputs

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle (pre/post execution, state changes)

**Utilities** (`./askr/utils/`)
- Shared helpers (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local filesystem storage for session state, conversation history, and user configuration
- **Environment variables** — API keys, provider credentials (read in `usage_api.py`)

## External Integrations
- **LLM providers** — Accessed via `./askr/clients/`; subprocess calls in `usage_api.py` likely invoke provider CLIs or APIs
- **IDE/editor** — Bidirectional communication through `./askr/ide/`
- **System subprocess** — `subprocess` module in `usage_api.py` executes shell commands

## Key Call Chains
1. CLI command → `./askr/cli/` → `./askr/session/usage_api.py`
2. `usage_api.py` → `./askr/state/` (load/save) → `./askr_state/`
3. `usage_api.py` → `./askr/clients/` (LLM calls)
4. `./askr/clients/` → `./askr/hooks/` (notify on completion)
5. `./askr/hooks/` → `./askr/notifications/` (alert user)

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any schema changes affect session persistence; impacts all modules reading state
- **`./askr/clients/`** — Message format changes propagate to CLI, hooks, and QA
- **`./askr/utils/`** — Shared validation/logging utilities; changes affect all consumers
- **`./askr_state/` directory structure** — Alters how all modules persist/retrieve data
