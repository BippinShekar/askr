Last updated: 2026-06-13 23:03

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It solves the problem of context loss and manual handoff friction in long-running AI-assisted coding workflows by maintaining session state, tracking token usage, and enabling autonomous continuation across interruptions.

## What's In Flight

- Handover system redesign: Root cause identified (stop checkpoint handler never invoked); requires architectural fix to ensure stale checkpoints don't poison autonomous sessions. Currently blocking reliable session continuation.
- Goal inference timing: Moving from message-aware auto-inference (which creates stale objectives) to session-aware inference deferred until session-end validation.
- Checkpoint card display verification: Testing that 'turns remaining' calculation displays correctly in staging before merging report_image.py fixes to main.
- Twitter/X launch strategy: Drafting solution-focused messaging and audience growth plan to support Phase 4 (Public Launch) milestone. Currently 5% complete; blocked on README context read.

## Key Decisions Made

- Checkpoint format flexibility: Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Delta extraction at hook level: Capture raw deltas in post_tool_use.py hooks rather than in checkpoint.py to separate