Last updated: 2026-06-13 22:58

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, managing state persistence, subprocess execution, and multi-client support. It solves the problem of context loss and manual coordination in AI-assisted coding by maintaining session state, tracking API costs, and enabling autonomous handovers between sessions.

## What's In Flight

- Cost aggregation and Discord notification system for `askr init` and snapshot generation. Currently API calls are scattered or unlogged; building unified cost tracking that sends notifications to Discord instead of terminal output.
- Handover system redesign. Root cause identified: stop checkpoint handler is never invoked, causing stale goals and missing handover state. Requires architectural fix, not incremental patching.
- Context checkpoint card display verification in staging. Need to confirm 'turns remaining' calculation displays correctly before pushing report_image.py fixes to main.

## Key Decisions Made

- Checkpoint system handles both dict and str goal formats for backward compatibility while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Goal inference is session-aware and deferred until session-end validation, not auto-inferred mid-session. Auto-inferred goals become stale and poison autonomous