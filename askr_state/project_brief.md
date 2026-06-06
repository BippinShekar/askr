Last updated: 2026-06-06 22:13

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Phase 3.6 guard system: autonomous error correction where the guard detects Claude mistakes, sends pre/post-correction screenshots to Discord, and helps Claude understand proper structure. Implementation exists in `askr/hooks/pre_tool_use.py`, `askr/session/guard.py`, `askr/hooks/guard_runner.py` across 4 commits.
- Bug fix: AppleScript string quoting in goal creation command (`askr/session/lifecycle.py`) — inner double quotes need to be single quotes for proper wrapping.
- Bug fix: Terminal.app launch from goal creation runs headless — needs `activate` call in AppleScript to bring window to foreground so Claude session chat is visible.
- End-to-end test of Stage 10 project brief generation with real checkpoint.

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files, enabling developer handoffs without external databases.
- Guard system runs as pre-tool-use