Last updated: 2026-06-15 22:12

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It enables developers to collaborate with AI on code tasks, maintaining session state across interruptions and automatically continuing work when context limits are hit.

## What's In Flight

- End-to-end validation of context-cut autonomous session launch: trigger 75% context limit in research session and verify talk-only continuation launches immediately with inferred direction
- Pre-compact hook timing verification: confirm hook fires before context compaction and blocks auto-compaction when direction_proposal is pending
- Integration test coverage for research → context-cut → autonomous continuation scenario to prevent regression
- Daemon log rotation and retention review to ensure full visibility into lifecycle events for future debugging

## Key Decisions Made

- Auto-launch talk-only sessions on context-cut without user approval gate. Context limit is a hard constraint; delaying autonomous continuation defeats seamless handover.
- Keep direction_proposal notification for user visibility but decouple from launch gate. Users see inferred direction but don't block session start.
- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers rather than git diffs alone. These files control autonomous session continuation.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid