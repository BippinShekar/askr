Last updated: 2026-06-11 13:31

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It then orchestrates resumption in a fresh session with a handover document, enabling seamless developer handoffs and long-running coding tasks that exceed single-session limits.

## What's In Flight

- Daemon bytecode caching fix: stop.py and lifecycle.py changes are on disk but stale code is running in the long-lived daemon process. Requires launchctl restart to load new bytecode and verify end-to-end session auto-resumption.
- Session card display: deciding whether to show git remote or directory name in card top-right for clarity in multi-project workflows.
- Discord integration: generating sample session card image and update message for team visibility.
- Daemon restart detection: adding safeguards to prevent stale code execution after daemon restarts.

## Key Decisions Made

- State persisted to git, not database: enables handoffs between developers and sessions without external infrastructure.
- Append-only decision log: all decisions recorded with timestamp and rationale; never edited, only appended.
- Checkpoint triggered before exhaustion, not after: forecast module predicts which limit hits first (context or quota) and pauses safely before hitting it.
-