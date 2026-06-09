Last updated: 2026-06-10 03:23

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before triggering a clean session restart. It solves the problem of losing work mid-session and enables seamless handoffs between developers by maintaining persistent project context in version control.

## What's In Flight

- Session restart mechanism for pre-compact hook: rewritten to terminate Claude process via PID file after checkpoint, allowing new session to start with fresh context instead of in-session compaction.
- WebSearch tool seeding in CLI: modified `askr init` to include WebSearch in baseline allowed tools for all new projects.
- Verification of pre_compact.py behavior: need to confirm PID file reading, process termination, and clean session restart work end-to-end without manual intervention.

## Key Decisions Made

- Checkpoint + restart approach chosen over in-session compaction: compaction within the same session defeats the purpose of context reset, so we trigger Claude process termination instead.
- State persistence via git: all project context, decisions, and progress stored in version control to enable developer handoffs and session resumption.
- Hook-based integration: Claude Code integration points (session start, prompt submit, session stop, pre-compact) allow non-invasive monitoring and intervention.
- PID