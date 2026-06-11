Last updated: 2026-06-11 12:55

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume autonomously without cold-start discovery.

## What's In Flight

- Resolving session lifecycle contradiction: extended thinking sessions block the 20-second silence detection that triggers safe kills, causing mid-turn interruptions. Current work is implementing a kill guard in `_wait_for_exchange_end_then_kill()` to detect extended thinking blocks and defer termination.
- Fixing handover mechanism: new sessions currently receive only a pointer to handover files, not content. Need to pass full context to `_start_claude()` for autonomous continuation.
- Daemon restart detection to prevent stale code execution after daemon restarts.
- Verification of auto-continue switch firing in askr repo after daemon trigger.

## Key Decisions Made

- Context exhaustion threshold set to 65% (changed from 50%) to provide buffer before Claude's auto-compaction kicks in and breaks context preservation.
- Append-only decision log in decisions.md to maintain audit trail of all architectural choices.
- State persisted in git (tasks, decisions, progress) rather