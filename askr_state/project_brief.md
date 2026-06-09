Last updated: 2026-06-09 22:03

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or momentum.

## What's In Flight

- Emergency checkpoint implementation during pre-compact hooks: detecting when Claude auto-compacts context and saving state before it happens.
- Kill/restart flow analysis in lifecycle.py: investigating why askr killed a Claude session in the leaps repo but failed to auto-restart it, leaving the session stopped instead of recovering.
- State persistence layer: completing reader.py and writer.py to load and update developer context from git-backed state files.
- Hook integration: wiring session_start.py, user_prompt_submit.py, and stop.py to inject context, extract objectives, and generate handover docs on session end.

## Key Decisions Made

- State stored in git, not a separate database: enables version control, diffs, and handoffs without external infrastructure.
- Append-only decisions log: all decisions recorded with timestamp and reason; never edited, only appended.
- Safe pause validation before checkpoint: safe_pause.py ensures interruption happens at a stable point, not mid-operation.