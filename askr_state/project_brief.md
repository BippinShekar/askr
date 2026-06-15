Last updated: 2026-06-15 13:53

# Project Brief

Askr is a CLI-based AI coding agent that manages development sessions, handles user interactions, and tracks usage metrics. It integrates with IDEs and external LLM services to provide autonomous code generation and task completion, with session state persisted locally and usage tracked via subprocess telemetry.

## What's In Flight

- Fixing Discord webhook prompt on fresh installs: moved prompt logic outside exception handler to guarantee execution when no .env file exists. Awaiting verification on clean clone.
- Verifying context checkpoint cards display correct "turns remaining" calculation in staging environment before pushing report_image.py fixes to main.
- Handover system architectural redesign: current checkpoint timing causes stale goals in autonomous session continuation. Root cause identified as missing stop checkpoint handler invocation, not race conditions.
- Goal inference timing fix: deferring inference to session-end validation rather than mid-session auto-inference to prevent stale objectives from poisoning autonomous handovers.

## Key Decisions Made

- Checkpoint system handles both dict and str goal formats for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Checkpoint and launch_mode files are primary handover state carriers; git diffs