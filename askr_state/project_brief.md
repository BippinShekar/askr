Last updated: 2026-06-15 13:58

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It orchestrates subprocess execution, maintains session state across invocations, and bridges code editors with AI backends to enable autonomous and interactive coding workflows.

## What's In Flight

- Fixing handover system for autonomous session continuation: checkpoint cards were displaying stale goals and turns remaining due to goal inference timing and missing stop checkpoint handler invocation. Architectural redesign underway to defer goal inference until session-end validation and ensure checkpoint creation always executes.
- Verifying context checkpoint cards display correct turns remaining in staging environment before pushing fixes to main.
- Debugging askr init Discord webhook prompt: moved prompt outside try-except block and fixed .env loading to search from repo root instead of current working directory. Awaiting end-to-end validation from user.

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone. These files control autonomous session continuation and are the primary source of truth for session resumption.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session from old user messages. Auto-inferred goals are tagged at inference time in session_start.py to distinguish them from user-created