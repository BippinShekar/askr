# Architecture

*Auto-generated at checkpoint — 2026-06-13 18:04 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, handles notifications, and integrates with IDEs for code analysis and generation.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions and tracks usage via subprocess calls and platform detection

## Core Modules

### Session Management (`./askr/session/`)
Manages user sessions, state persistence, and API interactions. `usage_api.py` orchestrates session lifecycle and collects environment metadata (OS, Python version).

### CLI (`./askr/cli/`)
Command-line interface layer. Parses user input and routes to appropriate handlers.

### State Management (`./askr/state/`)
Persists and retrieves session state. Likely reads/writes to `./askr_state/` directory.

### Clients (`./askr/clients/`)
External service integrations (LLM APIs, code analysis services). Abstracts HTTP/RPC communication.

### IDE Integration (`./askr/ide/`)
Bridges with IDEs (VSCode, JetBrains, etc.). Handles code context extraction and inline suggestions.

### Notifications (`./askr/notifications/`)
Delivers alerts and status updates to users (desktop notifications, terminal output).

### QA (`./askr/qa/`)
Quality assurance and validation logic. Likely includes code review, test generation, or output verification.

### Hooks (`./askr/hooks/`)
Git/IDE event listeners. Triggers workflows on file changes, commits, or IDE events.

### Utilities (`./askr/utils/`)
Shared helper functions (logging, formatting, file I/O).

## Data Stores
- **`./askr_state/`** — Local session state, cache, and configuration
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots
- **`./.claude/`** — Claude-specific configuration or credentials

## External Integrations
- **LLM APIs** (via `./askr/clients/`) — Code generation and analysis
- **IDE protocols** (via `./askr/ide/`) — Editor communication
- **Git** (via `./askr/hooks/`) — Repository event hooks
- **System subprocess** (via `usage_api.py`) — OS-level operations

## Key Relationships
```
usage_api.py (entry)
  → session/ (lifecycle)
    → state/ (persistence)
    → clients/ (LLM/external calls)
    → cli/ (user input)
      → ide/ (context)
      → qa/ (validation)
      → hooks/ (events)
  → notifications/ (output)
```

## Shared Interfaces
- **`./askr/state/`** — All modules read/write session state; changes affect persistence across CLI, IDE, and hooks
- **`./askr/clients/`** — Shared API client; changes impact all external integrations
- **`./askr/utils/`** — Utility functions used across all modules; breaking changes propagate widely

## Testing & Stress
- **`./stress-tests/`** — Load/performance tests for session and API layers
