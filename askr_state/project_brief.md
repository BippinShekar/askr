Last updated: 2026-06-11 14:13

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without context loss or manual setup.

## What's In Flight

- Fix daemon context overflow during active chat: 80% hard override in lifecycle.py prevents indefinite waits when context climbs past threshold while daemon is idle (COMPLETED, pushed to main).
- Fix workspace-mismatched extension notifications triggering unwanted session opens: added path validation to extension.js notification handler (COMPLETED, reloaded into ~/.cursor/extensions/).
- Generate Discord update message with sample session card image for team visibility.
- Verify test status from last Bash output and fix any failures.
- Decide: display git remote or directory name in card top-right for clarity.

## Key Decisions Made

- State is append-only and persisted to git: decisions.md, .askr_history, and task files are source of truth for session continuity across developers.
- Checkpoint triggers at 80% context usage during active chat, not at auto-compact time, to prevent race conditions and indefinite JSONL exchanges.
- Extension only processes notifications matching its workspace