# Architecture

*Auto-generated at checkpoint — 2026-06-15 08:38 UTC*

# Architecture

## System Purpose
Askr is a CLI-based AI coding agent that manages interactive sessions, tracks usage metrics, and integrates with IDE/client environments for code analysis and assistance.

## Entry Points
- **`./askr/session/usage_api.py`** — Primary execution point; handles session initialization, usage tracking, and subprocess orchestration via CLI commands.

## Core Modules

### Session Management (`./askr/session/`)
Manages user sessions, state persistence, and usage tracking. `usage_api.py` coordinates session lifecycle and metrics collection.

### CLI (`./askr/cli/`)
Command-line interface layer. Parses user input and routes to appropriate handlers.

### State Management (`./askr/state/`)
Persists and retrieves session state. Likely reads/writes to `./askr_state/` directory.

### Clients (`./askr/clients/`)
Abstractions for external integrations (LLM APIs, code analysis services). Handles authentication and request/response formatting.

### IDE Integration (`./askr/ide/`)
IDE-specific adapters (VSCode, JetBrains, etc.). Enables bidirectional communication with editor environments.

### Notifications (`./askr/notifications/`)
Handles user alerts and feedback delivery (console, IDE popups, webhooks).

### QA (`./askr/qa/`)
Quality assurance and validation logic for code suggestions and analysis results.

### Hooks (`./askr/hooks/`)
Event handlers for lifecycle events (pre/post-execution, error handling).

### Utilities (`./askr/utils/`)
Shared helper functions (logging, formatting, file I/O).

## Data Stores
- **`./askr_state/`** — Local session state storage (JSON/YAML configs, session metadata).
- **`./Formula/`** — Likely template or configuration definitions for code generation/analysis rules.

## External Integrations
- **LLM APIs** — Via `./askr/clients/` (OpenAI, Anthropic, or similar).
- **IDE/Editor APIs** — Via `./askr/ide/` for VSCode/JetBrains integration.
- **Subprocess execution** — `usage_api.py` spawns child processes for code execution/analysis.

## Key Call Chains
1. CLI input → `./askr/cli/` → `./askr/session/usage_api.py`
2. `usage_api.py` → `./askr/state/` (load session) → `./askr/clients/` (query LLM)
3. LLM response → `./askr/qa/` (validate) → `./askr/ide/` (send to editor) or `./askr/notifications/`
4. Hooks triggered at each stage via `./askr/hooks/`

## Shared Interfaces (High-Impact Changes)
- **`./askr/session/usage_api.py`** — Core orchestrator; changes affect all execution paths.
- **`./askr/state/`** — State schema changes break session persistence across all modules.
- **`./askr/clients/`** — API contract changes propagate to all LLM-dependent features.
- **`./askr/ide/`** — IDE protocol changes affect editor integration across all features.
