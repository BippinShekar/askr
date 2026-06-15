# Architecture

*Auto-generated at checkpoint — 2026-06-15 11:12 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with context awareness and usage tracking.

## Entry Points
- `./askr/session/usage_api.py` — Primary execution point; handles session initialization, subprocess management, and platform-specific operations

## Core Modules

**CLI Layer** (`./askr/cli/`)
- Command parsing and user interaction interface
- Routes commands to appropriate session handlers

**Session Management** (`./askr/session/`)
- `usage_api.py` — Orchestrates session lifecycle, spawns subprocesses, collects platform/environment data
- Manages session state persistence and recovery

**State Management** (`./askr/state/`)
- Maintains in-memory and persisted application state
- Tracks session context, user preferences, execution history

**Client Integrations** (`./askr/clients/`)
- Abstractions for external AI/LLM services
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Editor/IDE interaction layer
- File operations, syntax awareness, code analysis

**Notifications** (`./askr/notifications/`)
- User alerts and status updates
- Session event broadcasting

**Hooks** (`./askr/hooks/`)
- Lifecycle event handlers (pre/post execution, state changes)
- Plugin extension points

**QA** (`./askr/qa/`)
- Code validation and testing utilities
- Output verification before user presentation

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, file I/O)
- Cross-module dependencies

## Data Stores
- `./askr_state/` — Persistent session state directory (JSON/config files)
- `./.llm_snapshot/` — Cached LLM responses and context snapshots
- `./.claude/` — Agent-specific metadata and configuration

## External Integrations
- LLM APIs via `./askr/clients/`
- IDE/editor communication via `./askr/ide/`
- System subprocess execution via `usage_api.py`

## Key Call Chains
1. CLI entry → `usage_api.py` → Session initialization
2. Session → State manager → Persistent storage
3. Session → Client layer → LLM API
4. Session → IDE layer → File operations
5. Hooks trigger notifications on state changes
6. QA validates outputs before returning to user

## Shared Interfaces (High-Impact Changes)
- `./askr/state/` — All modules depend on state schema; changes cascade widely
- `./askr/clients/` — Response format changes affect CLI, IDE, QA layers
- `./askr/utils/` — Utility function signatures used across all modules
- `./askr/session/usage_api.py` — Session lifecycle contracts affect hooks, state, clients

## Build/Runtime
- Python 3.x with venv isolation (`./venv/`)
- Stress tests in `./stress-tests/` for load validation
- Formula directory contains deployment/packaging logic
