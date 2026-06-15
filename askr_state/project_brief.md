Last updated: 2026-06-15 17:52

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, tracks token usage, and hands off work to autonomous follow-up sessions. It integrates with IDEs and notification systems to keep developers in the loop. The core problem: developers need an AI agent that understands project context, respects token budgets, and knows when to ask for human direction versus proceeding autonomously.

## What's In Flight

- Direction inference system: validating the three-signal chain (dirty files, blockers.md, handover next_actions) that determines whether an autonomous session has enough context to proceed without human confirmation
- Handover state persistence: ensuring checkpoint_pending.json and launch_mode.json correctly carry session state across autonomous boundaries
- Session lifecycle gate: confirming direction_confirm HITL gate blocks autonomous starts when confidence < 0.70, preventing token waste on empty-context sessions
- Uncommitted state files ready for commit: implementation_state.md and notifications.log document current validation work

## Key Decisions Made

- Direction inference uses three independent signals rather than a single source—provides redundancy and prevents false negatives when one signal is stale
- Confidence threshold of 0.70 triggers human confirmation gate, not autonomous session start—prevents wasting tokens on sessions with insufficient context
- Checkpoint and handover state are primary handover