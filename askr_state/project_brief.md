Last updated: 2026-06-16 03:09

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with Claude, analyzing code and generating solutions. It manages session state, integrates with LLM APIs, and handles autonomous handovers between sessions so work can resume without context loss. The core problem: keeping multi-session coding workflows coherent when Claude instances run concurrently across different projects.

## What's In Flight

- Multi-session daemon refactor: verified per-project cooldown tracking works in live testing (both /askr and /leaps logged independently in same 30s poll cycle). Dead single-project _read_stats() function removed and pushed.
- Handover system redesign: root cause identified as logic gap where stop checkpoint handler never invokes. Goal inference must be deferred to session-end validation, not auto-inferred mid-session, to prevent stale objectives poisoning autonomous handovers.
- Hook payload inspection for delta extraction: implemented at post_tool_use.py level to separate concerns between raw delta capture and checkpoint persistence.

## Key Decisions Made

- Per-project last_trigger_at dict in lifecycle.py instead of single float: enables independent cooldown state for each active project, fixing concurrent session abandonment.
- Checkpoint and launch_mode.json are primary handover state carriers, not git diffs alone: investigation revealed these files control autonomous continuation; git state