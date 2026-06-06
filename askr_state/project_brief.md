Last updated: 2026-06-06 21:54

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and generating handover docs that let anyone resume work without context loss.

## What's In Flight

- Integration test suite for all 4 stages of the checkpoint/resumption pipeline (stages 7-10). Currently 7-10 tests written, need CI pipeline validation and real end-to-end testing with actual checkpoints.
- Stage 10 project brief generation: verifying that the handover document is correctly generated from persisted state at session end.
- AppleScript string escaping fix in `lifecycle.py`: goal text containing apostrophes (e.g., "askr's") was breaking the Claude session launcher. Implemented temp shell script approach to avoid quote conflicts.
- Test status verification: need to check last Bash output for any test failures and fix them.

## Key Decisions Made

- State persisted to git, not a database. Enables version control, diffs, and natural handoffs between developers.
- Append-only decision log in `decisions.md`. Never edit existing lines; only append. Maintains audit trail of why choices were made.