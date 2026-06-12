# Architecture

*Auto-generated at checkpoint — 2026-06-12 15:05 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics via subprocess calls and platform detection
- **CLI commands** — `./askr/cli/` module provides command-line interface for user interactions

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess execution and OS-level metrics

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history, context, and execution state across invocations

**Client Integrations** (`./askr/clients/`)
- Abstracts LLM provider communication (likely OpenAI, Anthropic, or similar)
- Handles request/response serialization and error handling

**IDE Integration** (`./askr/ide/`)
- Bridges between agent and development environment
- Likely handles file operations, code analysis, and editor communication

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates
- Decouples notification logic from core execution

**QA/Testing** (`./askr/qa/`)
- Validation and testing utilities for agent outputs
- Likely includes prompt validation and response verification

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle (pre/post execution, state changes)
- Enables extensibility without modifying core modules

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local filesystem storage for session state, conversation history, and execution context
- **External LLM APIs** — Integrated via `./askr/clients/` (credentials likely from environment variables)

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle management)
  ├→ state/ (persistence to ./askr_state/)
  ├→ clients/ (LLM communication)
  ├→ ide/ (file/environment operations)
  ├→ hooks/ (event callbacks)
  ├→ notifications/ (user alerts)
  └→ qa/ (output validation)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any schema changes affect session serialization across all modules
- **`./askr/clients/`** — LLM response format changes cascade to IDE, QA, and hooks
- **`./askr/hooks/`** — Event contract changes require updates in session, state, and notifications
- **`./askr/utils/`** — Utility function signatures affect all dependent modules

## External Dependencies
- **Subprocess execution** — OS-level command invocation via `usage_api.py`
- **Platform detection** — Cross-platform compatibility tracking
- **LLM APIs** — Remote inference via client integrations
