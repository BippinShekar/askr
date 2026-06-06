Last updated: 2026-06-06 21:48

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that Claude can resume from.

## What's In Flight

- Fixing `askr goal add` command to spawn Claude in a visible Terminal.app window instead of headless. Terminal.app AppleScript approach confirmed working; pending daemon reload and end-to-end test verification.
- Adding integration tests for all 4 stages (7-10) in CI pipeline to validate checkpoint/resumption flow.
- Stage 10 project brief generation end-to-end test with real checkpoint data.
- Verifying test status from last session and fixing any failures.

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and version control of context.
- Four-stage lifecycle: monitor token usage → forecast exhaustion → checkpoint safely → resume with injected context.
- Terminal.app AppleScript chosen over iTerm2 for visible session spawning (iTerm2 was failing silently).
- Append-only decisions.md log to maintain audit trail of architectural choices.
- State layer (reader/writer) abstracts persistence; hooks layer