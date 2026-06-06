Last updated: 2026-06-06 18:20

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or repeating analysis.

## What's In Flight

- Integration tests for all 4 stages (7-10) in CI pipeline; Stage 10 (project brief generation end-to-end) needs validation against real checkpoints
- Secrets scrubbing feature shipped: `_scrub_secrets()` in checkpoint.py filters Discord webhooks, API keys (sk-ant-, sk-proj-, sk-), Bearer tokens, and random strings before messages reach Haiku
- README.md updated with `askr report` command documentation
- Competitive analysis completed; decision made to defer website launch until install story is cleaner (currently requires hardcoded paths, venv setup, no brew install)

## Key Decisions Made

- State persists in git via append-only decision logs and state files (tasks, progress, context snapshots); enables true handoff between developers
- Four-stage lifecycle: session start (inject context), prompt submit (extract objectives), pre-compact (emergency checkpoint), session end (generate handover docs and commit)
-