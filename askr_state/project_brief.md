Last updated: 2026-06-13 23:16

# Project Brief

Askr is a CLI-based AI coding agent that solves context loss across development sessions. It maintains conversation history, agent decisions, and session state across machine switches, team handoffs, and long-running projects—letting developers resume work without re-explaining context to Claude or their co-founders.

## What's In Flight

- Handover system redesign: Moving from stale checkpoint creation to session-aware goal inference and proper stop-checkpoint handler invocation. Root cause identified as logic gap, not timing issue.
- Context checkpoint card display: Verifying "turns remaining" calculation displays correctly in staging before pushing report_image.py fixes to main.
- X launch strategy: Tweet copy finalized (sarcasm-driven, three-problem structure); curated follow list compiled; engagement plan ready for execution one week before public launch.

## Key Decisions Made

- Checkpoint format handles both dict and string goal formats for backward compatibility with existing sessions.
- Delta extraction happens at hook level (post_tool_use.py) rather than checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Goal inference deferred to session-end validation, not auto-inferred mid-session, to prevent stale objectives from poisoning autonomous handovers.
- Handover state carriers are checkpoint_pending.json and launch_mode.json, not git