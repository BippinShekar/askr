Last updated: 2026-06-12 18:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. When a new session starts, Askr restores that state so developers can hand off work seamlessly between sessions without losing context or progress.

## What's In Flight

- Fixing handover document truncation: token budget for Haiku model was too low (300 tokens), causing Next Action to be cut off mid-sentence. Three files staged with fixes to increase budget and reorder goal/handover priority in new session initialization.
- Testing Discord notification gating with _start_claude boolean return value.
- Testing Terminal.app keystroke fallback on macOS for actual Claude launch.
- Deciding whether to display git remote or directory name in session card UI.
- Generating sample Discord update message with session card image.

## Key Decisions Made

- State persists in git (not a database) to enable developer handoffs and version control integration.
- Session lifecycle split into five stages: monitor (token tracking), forecast (predict which limit hits first), checkpoint (save state), safe_pause (validate interruption point), lifecycle (trigger resumption).
- Claude Code integration via hooks at session start, user prompt submit, session stop, and pre-compaction.
- Haiku