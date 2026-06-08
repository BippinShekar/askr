Last updated: 2026-06-08 19:29

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Emergency checkpoint system triggered on last session; verify test status and fix any failures from Bash output
- Review files changed since last session and cross-reference against decisions.md
- Session lifecycle hooks (start, prompt submit, stop, pre-compact) are implemented; integration testing in progress
- State persistence layer (reader/writer/config) operational; validation of state file updates needed

## Key Decisions Made

- Append-only decision log in decisions.md; never edit existing lines, only append with timestamp and reason
- State stored in git commits with handover docs generated on session end; enables developer-to-developer and session-to-session continuity
- Forecast module predicts which limit (context or quota) hits first to trigger checkpoint at optimal time
- Safe pause validation required before interrupting sessions; prevents checkpoints at unsafe code points
- Context snapshots loaded via context_loader.py; qa/ module handles code analysis and project understanding

## Open Goals

- Verify test status from last Bash output and fix any failures
-