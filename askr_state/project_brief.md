Last updated: 2026-06-12 18:58

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. It then orchestrates resumption in a new session with full context restored. The problem it solves: developers lose work and context when Claude Code hits limits mid-task, and handoffs between sessions are manual and error-prone.

## What's In Flight

- Fix handover document truncation: MAX_TOKENS in claude.py is hardcoded to 300, causing Haiku to cut off mid-sentence. Root cause identified; needs increase to 1500-2000 minimum.
- Verify Discord notification gating works with _start_claude boolean return value.
- Test Terminal.app keystroke fallback on macOS with actual Claude launch (prompt initialization delay tuned from 8s back to 4s).
- Resolve goal/handover directive conflict: goal is now context-only, not a prompt override. Changes staged across claude.py, lifecycle.py, and stop.py.
- Generate sample Discord update message with session card image.

## Key Decisions Made

- State persists in git as append-only handover documents; developers and sessions are stateless, state is in the repo.
- Goal stored in state is context for Claude, never overrides