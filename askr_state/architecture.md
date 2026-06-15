# Architecture

*Auto-generated at checkpoint — 2026-06-15 10:05 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage, and integrates with IDEs and external services.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI commands.

## Core Modules

### Session Management (`./askr/session/`)
Manages user sessions, state persistence, and API interactions. `usage_api.py` is the orchestrator that coordinates other modules.

### CLI (`./askr/cli/`)
Command-line interface layer. Parses user input and routes to appropriate handlers.

### State Management (`./askr/state/`)
Persists and retrieves session state. Likely backed by `./askr_state/` directory for state storage.

### Clients (`./askr/clients/`)
External service integrations (API clients, LLM providers, etc.). Abstracts communication with remote systems.

### IDE Integration (`./askr/ide/`)
IDE-specific adapters and communication protocols. Enables editor integration for code analysis and modifications.

### Notifications (`./askr/notifications/`)
Handles user alerts and status updates across channels.

### QA (`./askr/qa/`)
Quality assurance and validation logic for code changes and responses.

### Hooks (`./askr/hooks/`)
Event handlers and lifecycle callbacks (pre/post execution, state changes).

### Utilities (`./askr/utils/`)
Shared helper functions and common logic.

## Data Stores
- **`./askr_state/`** — Session state persistence (likely JSON or database files).
- **`./Formula/`** — Configuration or template definitions (purpose unclear from structure; likely formula/prompt templates).

## External Integrations
- **Subprocess execution** — Runs shell commands via Python's `subprocess` module.
- **Platform detection** — Uses `platform` module for OS-specific behavior.
- **File I/O** — JSON-based configuration and state serialization.

## Key Relationships
```
usage_api.py (entry)
  ├→ cli/ (parse commands)
  ├→ session/ (manage context)
  ├→ state/ (load/save state)
  ├→ clients/ (external APIs)
  ├→ ide/ (editor communication)
  ├→ hooks/ (lifecycle events)
  ├→ qa/ (validation)
  └→ notifications/ (user feedback)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — Any state schema changes affect session persistence across all modules.
- **`./askr/clients/`** — API contract changes impact all modules using external services.
- **`./askr/utils/`** — Utility function signatures affect all consumers.
- **`./Formula/`** — Configuration format changes propagate to CLI, clients, and session handlers.

## Testing & Artifacts
- **`./stress-tests/`** — Load and performance testing.
- **`./venv/`** — Python virtual environment.
- **`./.llm_snapshot/`** — Cached LLM outputs or model snapshots.
- **`./.claude/`** — Claude-specific configuration or context.
