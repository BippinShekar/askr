Last updated: 2026-06-08 23:39

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without context loss or repeated setup.

## What's In Flight

- Emergency checkpoint implementation: completing the safe_pause validation logic and pre_compact hook integration to catch exhaustion before Claude Code's automatic context compaction triggers.
- State persistence refinement: ensuring reader.py and writer.py correctly load and update task/decision/progress files across session boundaries.
- Test suite validation: verifying all unit tests pass after recent changes and fixing any failures from the latest git diff.

## Key Decisions Made

- Append-only decision log in decisions.md: all product and architectural choices are recorded with timestamp, author, and reasoning. Never edit existing lines—only append. This creates an auditable trail for handoffs.
- Git as source of truth for state: all checkpoints, task updates, and progress snapshots are committed to the project repo, not stored in external databases. Enables offline work and natural version control.
- Hook-based integration with Claude Code: rather than modifying Claude's internals, Askr injects at session_start, user_prompt_submit,