Last updated: 2026-06-10 17:09

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that Claude can resume from.

## What's In Flight

- Session report card rendering: displaying project name in header and distinguishing user messages from API exchanges in the turns statistic (e.g. "2 messages (48 exchanges)"). Changes committed; verification complete.
- Daemon restart detection to prevent stale code execution after daemon restarts.
- Auto-continue switch verification in askr repo after daemon trigger.
- Test suite validation and failure fixes from last session.

## Key Decisions Made

- State persists in git via append-only decision logs and structured state files (tasks, decisions, progress). This enables context recovery across developer handoffs and session resumptions.
- Checkpoint triggers fire before context auto-compaction and at quota exhaustion thresholds, not on arbitrary intervals.
- Session lifecycle is managed through Claude Code hooks (session_start, user_prompt_submit, stop, pre_compact) rather than external polling.
- Report cards include project name, session metadata (developer, timestamp), and turn statistics to provide context for resumption.

## Open Goals

- Add daemon