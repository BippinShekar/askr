# Architecture

*Auto-generated at checkpoint — 2026-06-15 13:39 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution entry point; initializes sessions and tracks usage metrics via subprocess calls and platform detection.

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess execution and platform-specific operations

**CLI** (`./askr/cli/`)
- Command-line interface layer; parses user input and routes to session handlers

**State Management** (`./askr/state/`)
- Persists and retrieves session state; coordinates with `./askr_state/` directory for state artifacts

**Clients** (`./askr/clients/`)
- LLM client implementations; handles API communication with external models

**IDE Integration** (`./askr/ide/`)
- Editor/IDE interaction layer; enables code analysis and file operations

**Hooks** (`./askr/hooks/`)
- Event handlers for session lifecycle (pre/post execution, state changes)

**Notifications** (`./askr/notifications/`)
- User-facing alerts and status updates

**QA** (`./askr/qa/`)
- Testing and validation utilities for agent responses

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)

## Data Stores
- **`./askr_state/`** — Local session state storage (JSON/serialized format)
- **Environment variables** — Configuration via `os` module (API keys, paths)

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (model inference)
- **Subprocess execution** — System command invocation for code execution
- **File system** — Direct read/write for code artifacts and state

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (orchestration)
  ├→ state/ (persistence)
  ├→ clients/ (LLM communication)
  ├→ hooks/ (event handling)
  ├→ ide/ (code interaction)
  ├→ cli/ (user input)
  ├→ notifications/ (output)
  └→ utils/ (shared helpers)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — State schema changes affect session persistence across all modules
- **`./askr/clients/`** — LLM client interface changes impact all AI-dependent features
- **`./askr/utils/`** — Utility function signatures affect CLI, session, and hooks
- **`./askr/hooks/`** — Hook contract changes affect session lifecycle across all modules

## Configuration
- Virtual environment: `./venv/`
- Test suite: `./stress-tests/`
- Snapshots: `./.llm_snapshot/` (cached model outputs)
