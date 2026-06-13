# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:36 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics, and orchestrates subprocess execution across platforms (Linux/macOS/Windows).

## Core Modules

### Session Management (`./askr/session/`)
Manages session lifecycle, state initialization, and usage tracking. `usage_api.py` is the orchestrator that spawns and monitors development sessions.

### CLI (`./askr/cli/`)
Command-line interface layer. Parses user input and routes to appropriate handlers. Entry point for user interactions.

### State Management (`./askr/state/`)
Persists and retrieves session state. Likely uses `./askr_state/` directory for storage. Maintains context across CLI invocations.

### Clients (`./askr/clients/`)
Abstractions for external LLM/API communication. Handles request/response formatting and authentication.

### IDE Integration (`./askr/ide/`)
Bridges between the agent and IDE environments. Manages file operations, code analysis, and editor interactions.

### Hooks (`./askr/hooks/`)
Event-driven handlers for session lifecycle events (pre/post execution, state changes).

### Notifications (`./askr/notifications/`)
Delivers user-facing alerts and status updates (likely via CLI output or external channels).

### QA (`./askr/qa/`)
Quality assurance and validation logic. Likely includes test execution, code review, or output verification.

### Utilities (`./askr/utils/`)
Shared helper functions (logging, formatting, file I/O, platform detection).

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON or similar format based on `usage_api.py` imports).
- **`./.llm_snapshot/`** — Cached LLM responses or conversation history.
- **`./.claude/`** — Configuration or credentials for Claude integration.

## External Integrations
- **LLM APIs** — Accessed via `./askr/clients/` (likely Claude or OpenAI).
- **Subprocess execution** — `usage_api.py` spawns child processes for code execution.
- **File system** — IDE integration reads/writes project files.

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle)
  ├→ cli/ (user input)
  ├→ state/ (persistence)
  ├→ clients/ (LLM calls)
  ├→ ide/ (file operations)
  ├→ hooks/ (event handlers)
  └→ notifications/ (output)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any schema changes affect session persistence across all modules.
- **`./askr/clients/`** — API contract changes break LLM communication.
- **`./askr/utils/`** — Utility function signatures impact all consumers.
- **`./askr/hooks/`** — Event definitions affect session lifecycle handlers.
