Last updated: 2026-06-11 13:06

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It then resumes the session in a new Claude Code window with the checkpoint loaded, enabling seamless handoffs between developers and long-running coding tasks without losing context or progress.

## What's In Flight

- Automatic handover mechanism: capturing checkpoint results with prompts, threading handover file paths through the notification system, and auto-loading handover files with @file syntax in new sessions. Implementation complete across lifecycle.py, stop.py, and extension.js; end-to-end testing in progress.
- Daemon restart detection to prevent stale code execution after daemon restarts.
- Discord update message generation with sample session card image.
- Verification of auto-continue switch firing in askr repo after daemon trigger.

## Key Decisions Made

- State is persisted to git, not a database, to enable developer handoffs and version control integration.
- Session lifecycle is managed by hooks injected into Claude Code: session_start, user_prompt_submit, stop, and pre_compact.
- Handover files are auto-detected in the session directory and injected as @file syntax into the resumed session prompt.
- Checkpoint is triggered before context auto-compaction or quota