# Architecture

*Auto-generated at checkpoint — 2026-06-12 21:38 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle via subprocess and platform detection
- **CLI commands** — `./askr/cli/` modules expose user-facing commands

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Session orchestration, subprocess execution, platform abstraction
- Manages session state lifecycle and API interactions

**State Management** (`./askr/state/`)
- Persists and retrieves session state
- Interfaces with `./askr_state/` directory for state storage

**Client Handlers** (`./askr/clients/`)
- Multi-client abstraction layer for LLM integrations
- Routes requests to appropriate AI providers

**IDE Integration** (`./askr/ide/`)
- Code editor/IDE communication
- Handles file operations and context passing

**Notifications** (`./askr/notifications/`)
- Event-driven notification system
- Alerts on session state changes

**Hooks** (`./askr/hooks/`)
- Lifecycle hooks for session events
- Extensibility points for custom behaviors

**QA/Testing** (`./askr/qa/`)
- Quality assurance and validation logic

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Session state persistence (filesystem-based)
- **`./.llm_snapshot/`** — LLM interaction snapshots/caching
- **`./.claude/`** — Claude-specific configuration/cache

## External Integrations
- **Subprocess execution** — Via `subprocess` module in `usage_api.py`
- **Platform detection** — OS-specific behavior via `platform` module
- **LLM clients** — Abstracted through `./askr/clients/`

## Key Relationships
```
usage_api.py (entry)
  ↓
session/ (orchestration)
  ↓
state/ (persistence) ↔ askr_state/ (storage)
  ↓
clients/ (LLM routing)
  ↓
ide/ (code context)
  ↓
notifications/ (events)
  ↓
hooks/ (extensibility)
```

## Shared Interfaces
- **`./askr/state/`** — All modules reading/writing session state depend on this; changes affect session persistence across CLI, IDE, and clients
- **`./askr/clients/`** — Client abstraction layer; changes propagate to all LLM-dependent modules
- **`./askr/utils/`** — Utility functions used across all modules; breaking changes cascade widely
- **`./askr/session/usage_api.py`** — Core session contract; changes affect CLI entry points and state management

## Build/Environment
- Python package structure with `__pycache__` directories
- Virtual environment at `./venv`
- Stress tests in `./stress-tests/` for load validation
