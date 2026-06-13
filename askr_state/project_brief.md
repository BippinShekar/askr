Last updated: 2026-06-13 23:34

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state between runs and supporting multi-client integration. It solves the problem of maintaining context and continuity across long coding tasks by managing session lifecycle, tracking API costs, and enabling autonomous handovers where the agent can resume work without user intervention.

## What's In Flight

- Cost tracking and Discord notification ordering in cmd_init() — display API costs before Discord message, mark session start before first API call. 85% complete; awaiting git commit finalization and end-to-end testing.
- Verification that context checkpoint cards display correct 'turns remaining' in staging environment.
- Handover system architectural redesign — current implementation has timing gaps where stop checkpoint handler is not invoked, causing stale checkpoints. Goal inference must be deferred to session-end validation rather than auto-inferred mid-session.

## Key Decisions Made

- Checkpoint state carriers (checkpoint_pending.json, launch_mode.json) are primary handover controls, not git diffs alone. Investigation revealed these files determine autonomous session continuation.
- Goal inference is session-aware, not message-aware. Auto-inferring from old user messages creates stale objectives that poison autonomous handovers.
- Delta extraction happens at hook level (post_tool_use.py), not in