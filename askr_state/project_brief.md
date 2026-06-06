Last updated: 2026-06-06 22:34

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Fix `askr goal add` command to launch Claude sessions in VS Code integrated terminal (with Terminal.app fallback). Extension handler exists; daemon notification delivery needs debugging.
- Test Stage 10 project brief generation end-to-end with real checkpoint data.
- Verify test suite status and fix any failures from last session.

## Key Decisions Made

- State persists in git (not a database) to enable developer handoffs and session resumption without external infrastructure.
- Session monitoring happens in daemon; hooks integrate at Claude Code lifecycle points (session start, prompt submit, session stop, pre-compact).
- Checkpoints are triggered by forecast module predicting which limit (context or quota) will be hit first, not by reactive exhaustion.
- Append-only decision log in decisions.md prevents merge conflicts and maintains audit trail across handoffs.
- Terminal.app is fallback mechanism only; primary path is VS Code integrated terminal via extension notification.

## Open Goals

- Debug why extension does not receive `goal_launch` notification from lifecycle daemon