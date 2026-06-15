Last updated: 2026-06-16 03:56

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with LLM integration, state persistence, and multi-client support. It bridges user intent to autonomous code execution by managing session lifecycle, persisting state across interruptions, and coordinating with LLM providers and IDE workspaces.

## What's In Flight

- Handover system redesign: addressing stale checkpoint creation and goal inference timing. Root cause identified as logic gap where stop checkpoint handler is not invoked; requires architectural fix, not incremental patch.
- Goal inference refactoring: shifting from message-aware (stale) to session-aware inference, with auto-suggested goals tagged at inference time to distinguish from user-created goals.
- Multi-user adoption readiness: evaluating conflict resolution for shared mutable state files (decisions.md, goals.md, notifications.log) that create race conditions under concurrent co-founder pushes.
- Dynamic product_brief.md generation: designing script to synthesize brief from architecture.md, goals.md, and decisions.md on git pull, eliminating merge conflicts.

## Key Decisions Made

- Checkpoint and launch_mode.json are primary handover state carriers, not git diffs alone. Investigation revealed these files control autonomous session continuation; git state is insufficient.
- Goal inference must be session-aware, not message-aware. Auto