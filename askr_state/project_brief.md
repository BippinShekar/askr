Last updated: 2026-06-15 16:55

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with context awareness and usage tracking. It orchestrates LLM interactions, maintains session state across interruptions, and provides autonomous handover capabilities so work can resume without manual context re-entry.

## What's In Flight

- **Handover system redesign**: Current checkpoint creation is failing to capture session state at termination. Root cause identified as missing stop-checkpoint handler invocation. Requires architectural fix, not incremental patching.
- **Goal inference timing**: Auto-inferred goals are becoming stale mid-session because inference happens at message level rather than session-end validation. Must defer inference until session termination to keep objectives synchronized with actual progress.
- **Direction inference (Signal 3)**: Commit-frequency heuristic (counting touches to askr/ folder) is architecturally blind. Redesign required to use semantic file-change analysis—map changed files to work domains (session_lifecycle, reporting, inference, testing) instead of folder name patterns.
- **Session card display**: Checkpoint card rendering in report_image.py needs staging verification before main branch push.

## Key Decisions Made

- Checkpoint and launch_mode.json are primary handover state carriers; git diffs alone are insufficient for proper session resumption.
- Goal inference must be session-aware, not message-aware