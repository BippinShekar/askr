Last updated: 2026-06-06 21:37

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are approaching exhaustion, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that Claude can resume from.

## What's In Flight

- End-to-end testing of goal autonomy trigger: determining whether `askr goal add` should launch an immediate autonomous session or wait for 75% context overflow. User assertion is that goals should execute in isolation immediately, not on threshold. Codebase exploration started but grep for goal trigger logic in `/askr/cli/` incomplete.
- Integration tests for all 4 stages (7-10) in CI pipeline. Stage 10 (project brief generation) needs end-to-end verification with real checkpoint.
- Discord screenshot validation for goal functionality confirmation.

## Key Decisions Made

- State persisted to git via append-only decision log and handover documents. Enables context recovery across sessions and developers.
- Four-stage checkpoint lifecycle: safe pause validation, state persistence, handover doc generation, git commit. Prevents mid-task interruption.
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion.
- Goal storage in session state confirmed working. Trigger