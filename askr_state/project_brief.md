Last updated: 2026-06-06 21:20

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control.

## What's In Flight

- Guard system (Phase 3.5): PreToolUse hook for significance detection, Haiku cross-check engine, and async delivery via IDE popup and Discord. Fully deployed and verified.
- Integration test suite: Adding 7-10 tests across all 4 stages to CI pipeline; Stage 10 (project brief generation) needs end-to-end validation with real checkpoints.
- Test status verification: Confirming all recent test runs pass and fixing any failures from last session.

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of architectural choices.
- State persisted to git (tasks, decisions, progress) rather than external database for developer handoff portability.
- Three-stage guard system: significance detection at hook level, Haiku validation against architecture, async non-blocking delivery to avoid blocking IDE.
- Quota refresh behavior verified; statusline display shows current API quota (currently 5%).
- Safe pause validation required before checkpoint to ensure no mid-operation interruption.