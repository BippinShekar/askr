Last updated: 2026-06-13 22:32

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across sessions and supporting autonomous continuation. It bridges code editors, LLM providers, and local file systems to enable multi-turn coding workflows where the agent can pick up where it left off.

## What's In Flight

- Root-cause analysis of handover failures: checkpoint_pending.json is created with stale goal content, then read by autonomous sessions at the wrong time. Three critical design failures identified: stop checkpoint handler never executes, goal inference auto-infers from old user messages instead of current session state, and handover creation/read cycle is out of sync.
- Verification of context checkpoint card display showing correct "turns remaining" calculation in staging environment.
- Fixes to report_image.py for turns-until-auto-compact calculation pending staging verification and push to main.

## Key Decisions Made

- Checkpoint state carriers (checkpoint_pending.json, launch_mode.json) are the primary handover mechanism, not git diffs alone. Investigation revealed these files control autonomous session continuation.
- Goal inference must be deferred until session-end validation, not auto-inferred mid-session. Auto-inferred goals become stale and out of sync with actual progress.
- Handover system requires architectural redesign, not incremental fixes. Current behavior