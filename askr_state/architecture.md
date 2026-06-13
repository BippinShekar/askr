# Architecture

*Auto-generated at checkpoint — 2026-06-13 17:44 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics via subprocess calls and platform detection
- **CLI commands** — `./askr/cli/` directory contains command handlers that trigger session workflows

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates with OS-level subprocess execution

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history and execution context

**Client Handlers** (`./askr/clients/`)
- Abstracts LLM provider integrations (likely OpenAI, Anthropic, etc.)
- Handles request/response serialization

**IDE Integration** (`./askr/ide/`)
- Bridges between agent and development environment
- Manages file operations and code context

**Notifications** (`./askr/notifications/`)
- Delivers async alerts (completion status, errors)

**QA/Validation** (`./askr/qa/`)
- Tests generated code and validates outputs

**Hooks** (`./askr/hooks/`)
- Event listeners for session lifecycle (pre/post execution)

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/pickle format)
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots
- **`./.claude/`** — Claude-specific configuration or context

## External Integrations
- **LLM APIs** — Clients communicate with remote AI models
- **OS subprocess** — `usage_api.py` executes system commands via `subprocess` module
- **File system** — IDE module reads/writes project files

## Key Relationships
```
CLI commands → session/usage_api.py
    ↓
state/ (load/save context)
    ↓
clients/ (send prompts to LLM)
    ↓
ide/ (apply code changes)
    ↓
qa/ (validate outputs)
    ↓
notifications/ (alert user)
    ↓
hooks/ (trigger callbacks)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any schema changes affect all session consumers
- **`./askr/clients/`** — Response format changes break IDE and QA modules
- **`./askr/utils/`** — Utility function signatures used across all modules
- **`./askr/session/usage_api.py`** — Session initialization contract affects CLI and state management

## Build/Environment
- Python package structure with `__pycache__` directories
- Virtual environment at `./venv`
- Stress tests in `./stress-tests/` for load validation
