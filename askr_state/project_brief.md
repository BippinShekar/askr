Last updated: 2026-06-06 21:31

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. It then orchestrates resumption in a fresh session with full context restored. This solves the problem of losing work and context mid-project when Claude hits its limits.

## What's In Flight

- Integration tests for all 4 stages of the checkpoint/resume cycle (stages 7-10) in CI pipeline. Stage 10 (project brief generation end-to-end) needs real checkpoint testing.
- Daemon process tracking fix: updated `_kill_claude()` in `lifecycle.py` to find Claude processes by working directory match using `lsof`, since manually-started Claude instances don't have a tracked PID. This unblocks the Stop hook.
- Test status verification from last Bash output and fixing any failures.
- Review of files changed since last session and decision log.

## Key Decisions Made

- State persisted to git, not a database. Enables handoffs between developers and sessions without external infrastructure.
- Append-only decision log in `decisions.md`. Never edit existing lines; only add new decisions with timestamp, developer, and reason.
- Four-stage lifecycle: session start (inject context), user prompt (extract objectives), stop (generate