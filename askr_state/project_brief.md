Last updated: 2026-06-15 13:13

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client handovers. It bridges user commands, file operations, and LLM reasoning to automate coding tasks while maintaining conversation history and execution context across sessions.

## What's In Flight

- Discord webhook initialization flow: `askr init` now prompts for webhook URL if missing from global or repo config, saving to `~/.config/askr/.env`. Friend is testing end-to-end validation.
- Checkpoint card display verification in staging: confirming 'turns remaining' calculation displays correctly before pushing report_image.py fixes to main.
- Handover system architectural redesign: current checkpoint timing causes stale goals in autonomous session continuations; requires rethinking when goal inference happens (deferred to session-end, not mid-session).

## Key Decisions Made

- Global `~/.config/askr/.env` loads first, then repo `.env` as fallback. Prevents accidental commits of personal webhooks; allows user overrides.
- `askr init` must prompt for missing Discord webhook instead of silently failing. Improves UX by catching config gaps immediately.
- Goal inference is session-aware, not message-aware. Auto-inferred goals tagged at session start (session_start.