Last updated: 2026-06-11 19:33

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so anyone can resume exactly where the previous session left off.

## What's In Flight

- Fix double-session bug in daemon lifecycle where kill operation fails silently, causing fallback timer to spawn a new Claude session while the original is still running. Guards added to `lifecycle.py` in two places (`_wait_for_idle` and `_start_claude`). Changes staged, awaiting commit.
- VSCode extension workspace filter corrected to claim notifications only for askr repo.
- Daemon restart verification incomplete — need to confirm full launchctl restart sequence executed.

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and version history of decisions/progress.
- Checkpoint triggered before context auto-compaction or quota exhaustion, not after.
- Session lifecycle managed by hooks into Claude Code (session_start, user_prompt_submit, stop, pre_compact) rather than external polling.
- Forecast module predicts which limit (context or quota) hits first to prioritize checkpoint timing.
- Safe pause validation ensures