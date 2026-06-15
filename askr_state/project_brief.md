Last updated: 2026-06-15 17:56

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persists session state across restarts, and integrates with VSCode via a handover system. It solves the problem of context loss in long-running AI-assisted coding tasks by maintaining checkpoint state, tracking token usage, and enabling human-in-the-loop gates when the AI's confidence in next steps is low.

## What's In Flight

- Direction confirmation gate: implemented handler in stop.py and extension.js to prompt users via VSCode input box when inference confidence drops below 0.70, preventing token wastage on ambiguous autonomous sessions
- End-to-end testing of direction_confirm flow: verify VSCode UI integration, input capture, and handover.json persistence
- Signal chain validation: confirm that user input from direction_confirm flows into the next autonomous session as Signal 1
- Timeout and fallback behavior for direction_confirm: define what happens if user doesn't respond within 5 minutes

## Key Decisions Made

- Handover state lives in checkpoint_pending.json and launch_mode.json, not git diffs alone; these files control autonomous session continuation
- Goal inference is session-aware, not message-aware; auto-inferred goals are tagged at session_start.py to prevent stale objectives from poisoning handovers
- Direction