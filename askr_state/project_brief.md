Last updated: 2026-06-06 23:11

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control. The core problem: Claude Code sessions end abruptly when limits hit, losing work and context; Askr prevents that by predicting exhaustion and orchestrating safe pauses and resumptions.

## What's In Flight

- Goal launch notification fallback mechanism: VS Code extension attempts to intercept `goal_launch` notifications and open integrated terminal; Terminal.app always launches as guaranteed fallback if extension doesn't respond. Currently debugging why extension notification handler isn't firing despite notification being written to disk.
- Session lifecycle hooks fully wired: `session_start.py` injects context, `user_prompt_submit.py` captures objectives, `stop.py` generates handover docs and commits state, `pre_compact.py` emergency checkpoints before context auto-compaction.
- State persistence layer (`askr/state/`) reading and writing task/decision/progress files correctly; handover documents auto-generated on session end.

## Key Decisions Made

- Askr is Phase 1+ only: subcommands only (`goal`, `status`, `goals`, etc.). The `