Last updated: 2026-06-08 23:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent developer context, active objectives, and progress tracking in version control.

## What's In Flight

- Emergency checkpoint implementation: completing safe_pause.py validation logic and pre_compact.py hook integration to catch context exhaustion before Claude auto-compacts
- State persistence layer: finalizing reader.py and writer.py to load/update developer context, task lists, and decisions from git-tracked state files
- Session resumption flow: wiring lifecycle.py to inject prior context on session start and restore developer objectives from last checkpoint
- Test suite: verifying all modules pass unit tests and integration tests for checkpoint-resume cycle

## Key Decisions Made

- State stored in git as source of truth for developer handoffs; enables code review and audit trail of context/decisions across sessions
- Checkpoint triggered by forecast.py prediction (whichever limit hits first) rather than reactive; prevents mid-task interruption
- Hooks injected into Claude Code lifecycle (session_start, user_prompt_submit, stop, pre_compact) rather than external polling; tighter integration and lower latency
- safe_pause.py validates interruption safety