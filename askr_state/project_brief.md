Last updated: 2026-06-13 03:08

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client workflows. It bridges the gap between AI inference and actual code execution by managing conversation history, file operations, and IDE integration—letting developers collaborate with an AI agent that understands context across sessions.

## What's In Flight

- **Handover system analysis** — Diagnosing critical gaps in session handover creation that block stress-test readiness. Analysis initiated but not yet synthesized into actionable findings.
- **Stress-test preparation** — Infrastructure exists at `./stress-tests/` but readiness unknown; depends on handover system validation.
- **State persistence validation** — Ensuring session state serialization and recovery work reliably across session boundaries, particularly around transcript entry limits and context windows.

## Key Decisions Made

- **Filesystem-based state storage** — Session state lives in `./askr_state/` directory, not a database. Enables offline-first workflows and simplifies deployment.
- **Hook-driven extensibility** — Event callbacks (session_start, pre_compact, pre_tool_use) decouple features from core execution, reducing coupling and enabling third-party integrations.
- **Subprocess execution model** — LLM agent invokes OS commands via `usage_api.py