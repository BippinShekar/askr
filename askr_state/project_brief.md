Last updated: 2026-06-10 14:09

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Daemon restart and per-project stats verification: daemon was restarted after refactor that moved session stats from single `session_stats.json` to per-project files at `~/.config/askr/stats/`. Need to confirm daemon reads new stats correctly and fires auto-continue when context exceeds 50% threshold.
- Context trigger tuning: CONTEXT_TRIGGER lowered from 75% to 50% to catch exhaustion earlier. Current session at 73% context; auto-continue should fire on next tool use.
- Test status verification: confirm all tests pass after recent changes.

## Key Decisions Made

- Append-only decision log in decisions.md: never edit existing lines, only append. Maintains audit trail of why architectural choices were made.
- State persisted to git at session boundaries: checkpoint.py saves state before exhaustion, stop.py commits handover docs. Enables context recovery across developer handoffs.
- Per-project stats isolation: moved from global session_stats.json to per