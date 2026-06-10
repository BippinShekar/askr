Last updated: 2026-06-10 14:14

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before the session breaks. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) that Claude can resume from.

## What's In Flight

- Fixing context trigger mechanism: daemon was running stale code after per-project stats refactor, checking deprecated global session_stats.json instead of per-project files. Daemon restarted and now correctly fires triggers at 50% context threshold, but auto-continue switch has not yet occurred in askr repo (already working in leaps repo).
- Verifying test status from last bash output and fixing any failures.
- Reviewing files changed since last session and cross-checking against decisions.md.

## Key Decisions Made

- Per-project stats tracking: migrated from global session_stats.json to per-project files at ~/.config/askr/stats/ to support multiple concurrent projects. This broke daemon detection until restart.
- Context trigger threshold set to 50% (lowered from 75% → 65% → 50% through iteration).
- State persistence via git: all developer context, tasks, decisions, and progress stored in state files that are committed on session end, enabling handoffs without manual documentation