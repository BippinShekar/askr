Last updated: 2026-06-12 20:33

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM backend, persisting state across invocations and integrating with code editors. It orchestrates subprocess execution, manages session lifecycle, and bridges communication between the user's shell, IDE, and AI clients.

## What's In Flight

- Debug progress bar display issue: stats JSONL file not being populated or found after `askr init` with new pull. Path construction verified correct; next step is confirming PostToolUse hook in `.claude/settings.json` is triggering and tracing execution through `_find_active_jsonl`.
- Uncommitted changes in `implementation_state.md` and `notifications.log` from debugging session.

## Key Decisions Made

- Session lifecycle and subprocess orchestration centralized in `usage_api.py` as single entry point; all platform-specific logic flows through here.
- State persistence abstracted into `./askr/state/` module decoupled from session logic; enables clean reads/writes to `./askr_state/` filesystem store.
- Client communication abstracted via `./askr/clients/` to support multiple LLM providers; switching providers requires only new client implementation, not core changes.
- Hooks and notifications systems enable loose coupling; new event listeners can be added without modifying session or state