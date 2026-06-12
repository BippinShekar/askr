Last updated: 2026-06-12 20:35

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with LLM integration. It tracks API usage and state across multiple IDE environments, allowing developers to invoke AI assistance directly from their editor while maintaining session history and cost tracking.

## What's In Flight

- Progress bar display fix: `install.sh` was not creating Python venv or installing dependencies, causing `import rich` to fail silently post-pull. Modified `install.sh` to add venv creation and `pip install`. Awaiting verification that git commit completed and testing on fresh clone.
- Core session orchestration via `usage_api.py` is stable; focus is on ensuring initialization pipeline works end-to-end.

## Key Decisions Made

- Entry point is `./askr/session/usage_api.py` — all session lifecycle, usage tracking, and subprocess orchestration flows through here.
- State persists locally to `./askr_state/` as JSON; no remote backend. Configuration via environment variables.
- IDE communication uses subprocess execution with platform-aware adapters in `./askr/ide/`.
- LLM clients abstracted in `./askr/clients/` to support multiple model providers; response format is consumed by session, hooks, and QA modules.
- Hooks system (`./askr/hooks/`) fires pre/post execution