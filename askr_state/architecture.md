# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:48 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages development sessions, handles user queries, and integrates with IDE/notification systems.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; orchestrates session lifecycle, subprocess management, and platform-specific operations
- **`./askr/cli/`** — Command-line interface layer; routes user commands to appropriate handlers

## Core Modules

**Session Management** (`./askr/session/`)
- `usage_api.py` — Coordinates session state, subprocess execution, and OS interactions
- Manages session lifecycle and usage tracking

**State Management** (`./askr/state/`)
- Maintains application state persistence
- Interfaces with `./askr_state/` directory for state storage

**Client Integrations** (`./askr/clients/`)
- Handles external service communication (LLM providers, APIs)
- Abstracts client-specific logic from core logic

**IDE Integration** (`./askr/ide/`)
- Bridges IDE communication
- Likely handles editor-specific protocols or file operations

**Notifications** (`./askr/notifications/`)
- Manages user-facing alerts and status updates
- Decoupled from core logic

**Quality Assurance** (`./askr/qa/`)
- Testing and validation utilities
- May include prompt validation or response verification

**Utilities** (`./askr/utils/`)
- Shared helper functions across modules
- Platform detection, file operations, formatting

**Hooks** (`./askr/hooks/`)
- Event-driven handlers (likely git hooks or lifecycle callbacks)
- Triggers on specific system events

## Data Stores
- **`./askr_state/`** — Local state persistence (session data, configuration, cache)
- **`./Formula/`** — Likely prompt templates or configuration definitions
- **`./.llm_snapshot/`** — Cached LLM responses or model snapshots

## External Integrations
- **LLM Providers** — Via `./askr/clients/` (API calls for code analysis/generation)
- **IDE/Editor** — Via `./askr/ide/` (file operations, editor commands)
- **Git** — Via `./askr/hooks/` (version control integration)
- **OS/Subprocess** — Via `usage_api.py` (platform-specific execution)

## Key Call Chains
```
CLI (./askr/cli/) 
  → Session (./askr/session/usage_api.py)
    → State (./askr/state/)
    → Clients (./askr/clients/)
    → IDE (./askr/ide/)
    → Notifications (./askr/notifications/)
```

## Shared Interfaces (High Impact)
- **`./askr/state/`** — State schema changes affect session, clients, and persistence
- **`./askr/clients/`** — Client response formats consumed by session and IDE modules
- **`./askr/utils/`** — Utility changes propagate across all modules
- **`./Formula/`** — Prompt/config changes affect LLM behavior globally
