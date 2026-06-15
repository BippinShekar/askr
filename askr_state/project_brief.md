Last updated: 2026-06-16 03:38

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with an LLM, persisting conversation state and enabling multi-client support. It solves the problem of context loss during long coding sessions by maintaining session history, tracking token usage, and enabling autonomous handovers between sessions.

## What's In Flight

- Multi-project daemon monitoring: Verified working with independent per-project cooldown timers for askr and leaps projects. Refactored to remove dead single-project code.
- Handover system assessment: Currently reviewing daemon stability and roadmap phases to determine whether to proceed to next phase or address edge cases in current implementation.
- Session-aware goal inference: Recently shifted from message-level to session-level goal inference to prevent stale objectives in autonomous handovers.
- Checkpoint persistence: Fixed goal format handling to support both dict and string formats for backward compatibility.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause is that stop checkpoint handler was never invoked, making stale checkpoints a logic gap, not a timing issue.
- Goal inference deferred to session-end validation rather than auto-inferred mid-session. Auto-inferred goals become stale and out of sync with actual progress.
- Delta extraction happens at hook level (post_tool_use.py) rather