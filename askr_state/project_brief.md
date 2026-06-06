Last updated: 2026-06-07 05:20

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It solves the problem of losing work and context when a Claude Code session runs out of tokens mid-task, enabling seamless handoffs between developers and sessions.

## What's In Flight

- Phase 1 notification system: three-layer reliability (VS Code extension, Terminal.app fallback, direct logging) for alerting developers before context exhaustion.
- Phase 3 screenshot/report delivery: morning report system exists but untested in production; needs validation that Discord delivery and graph-adjacent formatting work end-to-end.
- Context limit stress-testing: user has not naturally approached 75% usage due to auto-summarization; need to artificially stress-test to verify checkpoint triggers fire correctly.
- Phase 4 decision pending: determine whether to proceed with advanced features or first validate Phase 3 delivery and stress-testing.

## Key Decisions Made

- Natural language Q&A routed through `ask` command, not `askr`; `askr` reserved for subcommands only (goal, status, goals, etc.).
- CONTEXT_TRIGGER threshold in lifecycle.py currently set above natural usage levels to avoid false positives during normal work.
- Append-