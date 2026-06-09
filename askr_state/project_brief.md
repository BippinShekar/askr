Last updated: 2026-06-09 21:43

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Token counting discrepancy investigation: root cause identified (in-flight extended thinking tokens not yet written to JSONL). Context threshold updated from 75% to 65% across forecast.py, lifecycle.py, extension.js, and report_image.py. Changes staged and ready for review.
- Emergency checkpoint implementation: needs completion and testing.
- Test suite validation: verify all tests pass after recent threshold changes.

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of all architectural choices.
- State persisted to git (not database) to enable developer handoffs and version control integration.
- Threshold logic accounts for in-flight tokens during Claude's turn, not just completed JSONL entries.
- Modular architecture: session lifecycle, hooks (Claude Code integration), state management, and QA analysis separated into distinct modules.
- Safe pause validation before checkpointing to avoid interrupting critical operations.

## Open Goals

- Complete and test emergency checkpoint implementation in askr/session