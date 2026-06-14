Last updated: 2026-06-14 14:27

# Project Brief

Askr is a CLI-based AI coding agent that manages development sessions, handles user queries, and integrates with IDEs and notification systems. It enables developers to offload coding tasks to an AI assistant while maintaining session state, tracking usage, and providing autonomous handover capabilities for multi-turn work.

## What's In Flight

- Remote session control and auto-run feature evaluation for team collaboration on 50-person teams. Currently assessing architectural feasibility, auth model constraints, and security implications before implementation planning.
- Handover system redesign to fix stale checkpoint generation. Root cause identified: stop checkpoint handler is not invoked at session end, causing auto-inferred goals to become out of sync with actual session progress.
- Goal inference refactoring to defer inference until session-end validation rather than mid-session auto-inference. Goals must be session-aware, not message-aware.
- Checkpoint card display verification in staging to confirm correct "turns remaining" calculation.

## Key Decisions Made

- Checkpoint system handles both dict and str goal formats for backward compatibility while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Checkpoint_pending.json and launch_mode.json are primary handover state carriers; git