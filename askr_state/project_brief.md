Last updated: 2026-06-14 10:11

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persists conversation state locally, and hands off work to autonomous follow-up sessions. It orchestrates subprocess execution, manages file operations through IDE integrations, and maintains session context across restarts via JSON-backed state files.

## What's In Flight

- Handover document freshness: completed tasks must be marked done or removed before next session reads handover.md, otherwise autonomous agents re-verify and waste tokens on duplicate work
- Checkpoint card display verification: confirm "turns remaining" metric displays correctly in staging environment before pushing report_image.py fixes
- Stage 2 roadmap: S1 is mostly complete; stages 2–5 need design and implementation
- Emoji removal from handover output: completed in code (writer.py, checkpoint.py, reader.py); handover.md task description needs to be updated to past tense or moved to completed section

## Key Decisions Made

- Handover state carriers (checkpoint_pending.json, launch_mode.json) are primary sources of truth for session continuation, not git diffs alone
- Goal inference is session-aware, not message-aware: auto-inferred goals are tagged at session start (session_start.py) to distinguish them from user-created goals and prevent stale objectives in autonomous hand