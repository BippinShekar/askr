Last updated: 2026-06-07 08:43

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) that Claude can resume from, solving the problem of losing context and momentum when a session ends or hits limits.

## What's In Flight

- Phase 3.7: Rich visual Disco mode for session monitoring (committed, in roadmap)
- Phase 3.8: Permission continuity across auto-started sessions (identified blocker: "allow once" grants from .claude/settings.json do not persist when Claude auto-resumes, breaking autonomous behavior)
- Context tracking mismatch investigation: askr showed 53% usage in external repo but auto-compact still fired, indicating JSONL monitoring or session_stats.json updates lag behind actual token burn
- Terminal auto-compact progress bar confirmed as available diagnostic tool (shows % till compaction and progress), but deemed secondary since askr's safeguards already stop well before auto-compact triggers

## Key Decisions Made

- Append-only decision log in decisions.md; never edit existing lines, only add new ones with timestamp and reasoning
- State persisted in git via checkpoint.py before exhaustion; handover docs generated on session