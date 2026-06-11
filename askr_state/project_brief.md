Last updated: 2026-06-11 20:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Refactoring Claude Code session lifecycle to use autonomous handover prompts instead of file-based handover paths. Lifecycle.py and stop.py updated; git commit pending completion with message "fix: drop handover_path parameter and dead code from lifecycle refactor".
- Generating Discord update messages with session card images for team visibility.
- Verifying test status from last Bash output and fixing any failures.
- Reviewing files changed since last session and cross-checking against decisions.md.

## Key Decisions Made

- Session state persists in git as append-only decision logs and task snapshots, enabling context recovery across developer handoffs.
- Handover prompts are now autonomous ("Read the handover and start on the Next Action immediately. Work autonomously.") rather than file-path-based, reducing coupling between session lifecycle and file system.
- Four integration hooks into Claude Code (session_start, user_prompt_submit, stop, pre_compact) capture context at critical points without requiring manual intervention.
- Token