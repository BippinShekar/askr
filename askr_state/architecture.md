# Architecture

*Auto-generated at checkpoint — 2026-06-15 12:58 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages user sessions, handles notifications, and integrates with IDE/client environments for code analysis and assistance.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes session tracking and usage metrics via subprocess calls and platform detection.
- **CLI commands** — `./askr/cli/` directory contains command handlers that route user input to appropriate services.

## Core Modules

**Session Management** (`./askr/session/`)
- Manages user sessions, authentication state, and session lifecycle
- `usage_api.py` tracks API usage and platform-specific metrics
- Persists session data to `./askr_state/` directory

**State Management** (`./askr/state/`)
- Maintains application state across requests
- Interfaces with session module for state persistence

**Clients** (`./askr/clients/`)
- Abstractions for external API integrations (LLM providers, code analysis services)
- Handles request/response serialization

**IDE Integration** (`./askr/ide/`)
- Bridges between Askr and IDE environments
- Manages editor-specific communication protocols

**Notifications** (`./askr/notifications/`)
- Handles user-facing alerts and status updates
- Integrates with system notification services

**QA/Testing** (`./askr/qa/`)
- Quality assurance utilities and test helpers

**Utilities** (`./askr/utils/`)
- Shared helper functions (logging, formatting, validation)

**Hooks** (`./askr/hooks/`)
- Event handlers and lifecycle callbacks

## Data Stores
- **`./askr_state/`** — Local state directory for session persistence and user data
- **In-memory state** — `./askr/state/` module manages runtime state

## External Integrations
- **LLM APIs** — Accessed via `./askr/clients/` (specific providers determined by client implementations)
- **IDE/Editor protocols** — Handled by `./askr/ide/`
- **System notifications** — OS-level integration via `./askr/notifications/`
- **Subprocess execution** — Used in `usage_api.py` for platform-specific operations

## Key Relationships
```
CLI (./askr/cli/) 
  → Session (./askr/session/) 
    → State (./askr/state/) 
      → Clients (./askr/clients/)
  → IDE (./askr/ide/)
  → Notifications (./askr/notifications/)
  → Utils (./askr/utils/)
```

## Shared Interfaces (High-Impact Changes)
- **`./askr/session/`** — Session contract affects all modules that read/write user context
- **`./askr/state/`** — State schema changes propagate to all consumers
- **`./askr/clients/`** — Client interface changes affect CLI and IDE modules
- **`./askr/utils/`** — Utility functions used across all modules
