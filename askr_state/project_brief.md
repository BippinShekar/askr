Last updated: 2026-06-11 22:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before pausing. When limits are hit, it orchestrates resumption by injecting prior context and objectives back into a new Claude session, enabling seamless handoffs between developers and across session boundaries.

## What's In Flight

- Autonomous session continuation: fixing prompt submission to Claude Code via Terminal.app fallback (CR vs LF line ending issue resolved in extension.js and lifecycle.py)
- Discord notifications on session resumption (gated on successful Claude launch)
- Verification of test suite status and fixing any failures from recent changes
- Decision: whether to display git remote or directory name in session card UI

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and version control integration
- Two-layer hook system: Claude Code hooks (session_start, user_prompt_submit, stop, pre_compact) feed into daemon lifecycle management (monitor, forecast, checkpoint, safe_pause)
- Terminal.app fallback for prompt submission uses two-step spawn + keystroke approach (claude process launched first, then prompt sent via osascript)
- Prompt submission requires CR line ending, not LF, to properly trigger Claude's input handler
- Session resumption