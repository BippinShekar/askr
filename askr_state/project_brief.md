Last updated: 2026-06-08 19:28

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Token usage reporting and visual card formatting for Discord: extracting input/output/cache tokens from session JSONL data and rendering metrics in Discord embeds with hero numbers, accent bars, and two-column layouts.
- Autonomous session detection: wiring detection logic through stop.py to identify when sessions run without developer interruption.
- Live verification of Discord card rendering and token field population from session data.

## Key Decisions Made

- State persisted to git as append-only decision logs and task files, enabling handoffs and audit trails.
- Session monitoring split into discrete modules: forecast.py predicts exhaustion, checkpoint.py persists state, lifecycle.py triggers resumption, safe_pause.py validates interruption safety.
- Claude Code integration via hooks at session start, prompt submission, session stop, and pre-compaction.
- Discord bot reports session metrics with token counts, turn count, duration, and developer interruption frequency.

## Open Goals

- Verify Discord card rendering on live channel and confirm all token fields populate correctly from