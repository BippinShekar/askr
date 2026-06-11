Last updated: 2026-06-11 20:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. When a session ends, it generates handover documentation so another developer (or the same one in a new session) can resume work without losing context or progress. The core problem it solves: Claude Code sessions are stateless and ephemeral, so developers lose their working context and have to re-explain their objectives every time they start a new session.

## What's In Flight

- Debugging autonomous session continuation: checkpoints are being created but resumption is broken. Root cause identified in commit cd774a3 (Jun 11, 13:41) where the launch command was changed to use @file attachment for handover injection instead of inline content. Previous working state (commit baa2d37) passed handover directly in the command string.
- Determining whether @file attachment mechanism is necessary or if Claude can read referenced files by name alone in the prompt.
- Reverting launch command structure in extension.js to restore autonomous continuation.
- Verifying test status and fixing any failures from recent changes.

## Key Decisions Made

- Session state is persisted in git (tasks, decisions, progress) to enable handoffs between developers and sessions.
- Checkpoint is triggered before context auto-compaction (