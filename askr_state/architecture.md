# Architecture

*Auto-generated at checkpoint — 2026-06-14 04:29 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; initializes sessions, tracks usage metrics, and orchestrates subprocess execution across platforms (Windows/Unix).

## Core Modules

**Session Management** (`./askr/session/`)
- Manages session lifecycle, state initialization, and usage tracking
- `usage_api.py` coordinates subprocess calls and platform-specific execution

**State Management** (`./askr/state/`)
- Persists and retrieves session state to `./askr_state/` directory
- Maintains conversation history and execution context

**CLI Interface** (`./askr/cli/`)
- Command parsing and user input handling
- Routes commands to appropriate handlers

**Client Integrations** (`./askr/clients/`)
- LLM client implementations (likely OpenAI, Anthropic, or similar)
- Handles API communication and response parsing

**IDE Integration** (`./askr/ide/`)
- Code analysis and file manipulation
- Workspace context awareness

**Notifications** (`./askr/notifications/`)
- User feedback and status updates
- Event-driven messaging

**QA Module** (`./askr/qa/`)
- Test execution and validation
- Code quality checks

**Hooks** (`./askr/hooks/`)
- Lifecycle callbacks (pre/post execution)
- Integration points for extensibility

**Utilities** (`./askr/utils/`)
- Shared helper functions and common operations

## Data Stores
- **`./askr_state/`** — Local session state persistence (JSON/structured files)
- **`./.llm_snapshot/`** — LLM interaction snapshots and conversation logs
- **`./.claude/`** — Claude-specific configuration or cache

## External Integrations
- LLM APIs via `./askr/clients/`
- Subprocess execution for code compilation/testing
- File system operations for IDE integration

## Key Relationships
```
usage_api.py (entry)
  ├→ session/ (state init & tracking)
  ├→ state/ (persistence)
  ├→ cli/ (command routing)
  ├→ clients/ (LLM communication)
  ├→ ide/ (code context)
  ├→ qa/ (validation)
  ├→ notifications/ (feedback)
  └→ hooks/ (callbacks)
```

## Shared Interfaces
- **State schema** (`./askr/state/`) — Changes affect session recovery and persistence across all modules
- **Client protocol** (`./askr/clients/`) — LLM response format used by CLI, QA, and IDE modules
- **Hook signatures** (`./askr/hooks/`) — Lifecycle events consumed by notifications and state management
- **Notification API** (`./askr/notifications/`) — Output format expected by CLI and session modules
