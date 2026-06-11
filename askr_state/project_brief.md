Last updated: 2026-06-11 13:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. On session resume, it injects the previous state and objectives back into Claude, enabling seamless handoffs between developers and across interrupted sessions without losing progress or context.

## What's In Flight

- End-to-end checkpoint→handover→resume flow: lifecycle.py auto-detects handover files and injects them as @file prompts; stop.py captures checkpoint results and builds handover prompts with next goals; extension.js wired to use checkpoint result payload.
- Handover file generation: verified that transcript generation logic produces complete, untruncated output when fed clean input (pre-fix: mid-extended-thinking kills truncated transcripts; post-fix: complete transcripts passed to Haiku).
- Race condition fix: identified PID file read/process probe race in _read_claude_pid(); needs daemon liveness check before execution.
- Test verification and git diff review from last session.

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and session resumption without external infrastructure.
- Checkpoint triggered before exhaustion, not after — forecast.py predicts which limit hits first and triggers safe_pause.