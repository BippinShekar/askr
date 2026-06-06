Last updated: 2026-06-06 21:46

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control. The core problem: Claude Code sessions are stateless and interrupt abruptly at limits, losing work and context. Askr makes sessions resumable and collaborative.

## What's In Flight

- Visible iTerm2 terminal execution for `askr goal add` command — currently modified to open a real window instead of running headless, pending verification that Claude session activity is visible to the user.
- Integration test suite for all 4 stages (7-10) in CI pipeline — tests for checkpoint generation, state persistence, and project brief generation end-to-end.
- Stage 10 project brief generation validation — needs end-to-end test with real checkpoint data.
- Test status verification from last Bash output and failure fixes.

## Key Decisions Made

- State is append-only and git-backed: all task updates, decisions, and progress are committed to version control to enable handoffs and audit trails.
- Checkpoint happens before exhaustion, not after: `safe_pause.py` validates safe interruption points; `pre_compact.py` triggers emergency