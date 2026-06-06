Last updated: 2026-06-06 21:39

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task state, decisions, and progress in version control.

## What's In Flight

- Autonomous session launch on goal creation: modify `askr goal add` to immediately spawn a new session with the goal as opening prompt, rather than waiting for context overflow at 75%
- End-to-end testing of goal functionality with Discord screenshots to verify the feature works as intended
- Integration tests for all 4 stages (7-10) in CI pipeline
- Stage 10 project brief generation end-to-end with real checkpoint data

## Key Decisions Made

- Goals inject into SessionStart context at the top of each session; they do not trigger new sessions on creation (current design being changed to support immediate execution)
- State persists in git via append-only decision logs and structured state files (goals.md, tasks.md, progress.md)
- Session lifecycle is managed by four modules: monitor (token tracking), forecast (limit prediction), checkpoint (state persistence), lifecycle (resumption orchestration)
- Safe interruption validation happens before any checkpoint to prevent mid-operation pauses
- Handover documents are auto-generated