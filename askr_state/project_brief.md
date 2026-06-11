Last updated: 2026-06-11 14:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without context loss or manual setup.

## What's In Flight

- Daemon restart detection: add logic to prevent stale code execution after daemon restarts
- Auto-continue verification: confirm the auto-continue switch fires in the askr repo after daemon trigger
- Test status validation: verify last Bash output and fix any test failures
- Session card UI: decide whether to display git remote or directory name in card top-right
- Discord integration: generate sample update message with session card image

## Key Decisions Made

- State persisted to git via append-only decision log and implementation state files, enabling handoffs across developers and sessions
- Context compaction uses hard-override threshold inside wait loop to prevent indefinite blocking when user remains actively chatting
- VSCode extension filters notifications by workspace path to prevent spurious Claude Code sessions in unrelated repos
- Session lifecycle split into discrete modules: monitor (token tracking), forecast (limit prediction), checkpoint (state persistence), lifecycle (resumption), safe_pause (interruption validation)
- Hooks injected at Claude Code boundaries: session_start