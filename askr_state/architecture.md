# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:42 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage, and integrates with IDE/notification systems for code analysis and assistance.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI commands

## Core Modules

### Session Management (`./askr/session/`)
Manages user sessions, state persistence, and usage metrics. `usage_api.py` is the main orchestrator that spawns subprocess calls and tracks execution context.

### CLI (`./askr/cli/`)
Command-line interface layer. Parses user input and routes to appropriate handlers. Called by entry point to execute user commands.

### State Management (`./askr/state/`)
Maintains application state across session lifecycle. Persisted to `./askr_state/` directory. Tracks context needed for multi-turn interactions.

### Clients (`./askr/clients/`)
External service integrations (likely LLM APIs, code analysis tools). Abstracts communication with remote services.

### IDE Integration (`./askr/ide/`)
Handles IDE-specific operations: file reading, code navigation, editor commands. Bridges between Askr logic and user's development environment.

### Notifications (`./askr/notifications/`)
Delivers user-facing messages and results. Handles formatting and delivery mechanism selection.

### QA (`./askr/qa/`)
Quality assurance and validation logic. Likely performs output verification, test execution, or response validation.

### Hooks (`./askr/hooks/`)
Lifecycle hooks for session events (pre/post execution, error handling). Extensibility points for custom behaviors.

### Utilities (`./askr/utils/`)
Shared helper functions: logging, file I/O, string processing, platform detection.

## Data Stores
- **`./askr_state/`** — Session state persistence (JSON/serialized format)
- **`./.llm_snapshot/`** — Cached LLM responses or conversation history
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **Subprocess execution** — Runs shell commands (detected in `usage_api.py` imports)
- **Platform detection** — OS-specific behavior via `platform` module
- **LLM APIs** — Via `./askr/clients/` (likely Claude/OpenAI)

## Key Relationships
```
usage_api.py (entry)
  ↓
cli/ (parse commands)
  ↓
session/ (manage context)
  ↓
state/ (persist data)
  ↓
clients/ (call LLM)
  ↓
ide/ (read/modify code)
  ↓
notifications/ (output results)
```

Hooks fire at session lifecycle points. QA validates outputs before notification. Utils provide cross-module support.

## Shared Interfaces
- **`./askr/state/`** — State schema changes affect session persistence and all modules reading state
- **`./askr/clients/`** — API contract changes impact CLI, session, and QA modules
- **`./askr/utils/`** — Utility function signatures affect all consumers
