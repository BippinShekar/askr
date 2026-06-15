# Architecture

*Auto-generated at checkpoint — 2026-06-15 21:39 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, invokes subprocess operations, and tracks platform/environment context

## Core Modules

**Session Management** (`./askr/session/`)
- Manages conversation state, session persistence, and usage tracking
- `usage_api.py` coordinates session initialization and execution flow

**CLI Interface** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate handlers

**Client Adapters** (`./askr/clients/`)
- LLM provider integrations (API clients for external AI services)
- Abstracts different model backends

**State Management** (`./askr/state/`)
- Persists session data, conversation history, and configuration
- Reads/writes to `./askr_state/` directory

**IDE Integration** (`./askr/ide/`)
- File system operations, code analysis, and editor interactions
- Bridges between session logic and local development environment

**Notifications** (`./askr/notifications/`)
- User feedback mechanisms (status updates, alerts)

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution)

**QA/Testing** (`./askr/qa/`)
- Validation and testing utilities

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, etc.)

## Data Stores
- **`./askr_state/`** — Local session state directory (conversation history, config, metadata)
- **In-memory state** — Active session context during execution

## External Integrations
- **LLM APIs** — Accessed via `./askr/clients/` adapters
- **Subprocess execution** — Shell command invocation (imported in `usage_api.py`)
- **File system** — Code reading/writing via `./askr/ide/`

## Key Call Chains
1. `usage_api.py` → `session/` → `state/` (load/save session)
2. `usage_api.py` → `cli/` (parse input)
3. `cli/` → `clients/` (query LLM)
4. `clients/` → `ide/` (fetch code context)
5. `ide/` → `state/` (persist changes)
6. Any module → `notifications/` (user feedback)

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Session schema; changes affect all modules reading/writing state
- **`./askr/clients/`** — LLM response format; changes cascade to CLI and session handlers
- **`./askr/ide/`** — File operation APIs; changes affect state persistence and code modifications
- **`./askr/utils/`** — Shared utilities; breaking changes propagate across all modules

## Test Structure
- **`./tests/`** — Unit and integration tests
- **`./stress-tests/`** — Load/performance testing
