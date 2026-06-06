Last updated: 2026-06-07 05:16

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, eliminating the friction of manual context recovery.

## What's In Flight

- Phase 1 validation: End-to-end test of morning report screenshot delivery mechanism. Currently unconfirmed whether screenshots actually arrive to user.
- Session orchestration subcommands (goal, status, goals, etc.) are operational and integrated with Claude Code hooks.
- Lifecycle notification flow: VS Code notification as primary, Terminal.app as fallback, headless as final layer. launchctl daemon currently unloaded.
- Token usage monitoring shows zero burnage due to auto chat window switching with pre-context summarization; user has not approached 90% session limit.

## Key Decisions Made

- State persisted to git via append-only decision log and handover documents, enabling developer handoffs without context loss.
- Four-layer architecture: session lifecycle (monitor, forecast, checkpoint, safe pause), Claude Code hooks (start, prompt submit, stop, pre-compact), persistent state (reader, writer, config), and code analysis (context loader, graph).
- Lifecycle notifications use layered fallback strategy: VS Code first,