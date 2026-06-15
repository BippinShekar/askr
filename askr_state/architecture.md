# Architecture

*Auto-generated at checkpoint — 2026-06-15 07:35 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, manages subprocess execution, and tracks platform/environment metadata
- **CLI commands** — `./askr/cli/` directory contains command handlers that dispatch to session and client modules

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state transitions, and usage tracking
- `usage_api.py` orchestrates subprocess calls and environment detection
- Persists session data to `./askr_state/` directory

**State Management** (`./askr/state/`)
- Maintains in-memory and persistent session state
- Interfaces with `./askr_state/` for serialization

**Clients** (`./askr/clients/`)
- Abstracts LLM provider communication (likely multiple provider implementations)
- Handles request/response formatting and streaming

**IDE Integration** (`./askr/ide/`)
- Bridges editor/IDE interactions
- Likely handles file operations and context extraction

**Notifications** (`./askr/notifications/`)
- Delivers user-facing alerts and status updates

**QA Module** (`./askr/qa/`)
- Quality assurance and validation logic for generated code/responses

**Hooks** (`./askr/hooks/`)
- Event-driven callbacks for session lifecycle events

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules

## Data Stores
- **`./askr_state/`** — Persistent session state directory (JSON or similar format)
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- **Subprocess execution** — Runs shell commands via Python's `subprocess` module
- **LLM APIs** — Clients communicate with external language models
- **Platform detection** — Uses `platform` module for OS/environment awareness

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (lifecycle management)
  │   ├→ state/ (persistence)
  │   └→ clients/ (LLM communication)
  ├→ cli/ (command routing)
  │   ├→ ide/ (file/editor context)
  │   ├→ notifications/ (user feedback)
  │   └→ qa/ (validation)
  └→ hooks/ (event callbacks)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/state/`** — Any state schema changes affect session persistence and all consumers
- **`./askr/clients/`** — LLM client interface changes propagate to session, CLI, and QA modules
- **`./askr/session/usage_api.py`** — Core orchestration; changes affect all entry paths
- **`./askr/hooks/`** — Event contract changes affect session, notifications, and IDE modules
