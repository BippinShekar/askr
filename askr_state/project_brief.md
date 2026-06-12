Last updated: 2026-06-12 19:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Building a rejection tracking system (`askr/validation/rejection_log.py`) to catch architectural violations in real-time before Claude implements them. Currently the implementation guard only records raw file modifications and bash commands without semantic validation.
- Wiring rejection tracking into checkpoint flow so each new session inherits rejection history and learns from past mistakes.
- Refactored goal completion detection to use Haiku-based parsing in handover generation instead of unreliable file-touch heuristics; checkpoint now passes open goals to Claude and parses completed goals from response.

## Key Decisions Made

- State is append-only and persisted in git (decisions.md, handover files, implementation_state.md) to enable developer handoffs and session resumption without data loss.
- Goal completion is determined by Haiku parsing of handover text, not by inferring from file activity — the latter was hitting token limits and producing false signals.
- Architecture validation must happen at suggestion time (pre-execution hook), not post-hoc, because by then Claude