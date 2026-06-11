Last updated: 2026-06-11 13:11

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Verifying that handover file generation produces meaningfully different output post-implementation (prompt field, checkpoint_result, handover_path references should now appear in generated files)
- Adding daemon restart detection to prevent stale code execution
- Testing auto-continue switch behavior in askr repo after daemon trigger
- Generating Discord update message with sample session card image
- Deciding on display format for git remote or directory name in card top-right

## Key Decisions Made

- State persists in git via append-only decision log and structured state files (tasks, progress, context snapshots)
- Session lifecycle is event-driven: hooks at session start, prompt submit, pre-compact, and stop trigger checkpoint/resumption logic
- Handover documents are generated at session end and committed automatically; they include active objectives, checkpoint results, and next actions
- Token forecasting predicts which limit (context or quota) will be hit first to trigger proactive checkpointing
- Safe pause validation ensures interruption only happens at safe