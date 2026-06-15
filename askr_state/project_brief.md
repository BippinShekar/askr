Last updated: 2026-06-15 14:19

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting multi-client integration. It bridges user intent to code execution by managing conversation history, file operations, and subprocess output while maintaining session continuity through JSON-backed state storage.

## What's In Flight

- Discord webhook error reporting: refactored send_message() to return (success: bool, error_message: str) tuple instead of swallowing HTTP errors; callers in askr.py and notification.py updated to unpack and log details. Awaiting git commit finalization and end-to-end testing with invalid webhook configuration.
- Context checkpoint card display: verifying that 'turns remaining' calculation displays correctly in staging before pushing report_image.py fixes to main.
- Handover system architectural redesign: current checkpoint timing creates stale goals in autonomous session continuation; requires rethinking when goal inference happens (session-end validation, not mid-session auto-inference) and ensuring stop checkpoint handler is always invoked.

## Key Decisions Made

- Checkpoint state carriers (checkpoint_pending.json, launch_mode.json) are primary handover truth, not git diffs alone. Investigation showed these files control autonomous continuation; git state is insufficient.
- Goal inference deferred to session-end validation rather than auto-inferred