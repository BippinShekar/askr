Last updated: 2026-06-16 03:48

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive sessions with an LLM, handles code analysis and generation, and integrates with IDEs and QA tools. It solves the problem of context loss and manual handoff friction when developers need to pause, resume, or hand off coding tasks to teammates or autonomous agents.

## What's In Flight

- Multi-project daemon monitoring with independent per-project cooldowns (validated working; no changes needed)
- Adoption blocker investigation: multi-user shared file conflicts and race conditions between askr and leaps (co-founder startup)
- Conflict resolution strategy design for concurrent writes to shared state files
- Determination of adoption priority: which system (askr or leaps) should be primary for co-founder sync

## Key Decisions Made

- Checkpoint and handover state are primary carriers of session continuation; git diffs alone are insufficient
- Goal inference must be session-aware and deferred to session-end validation, not auto-inferred mid-session from old messages
- Auto-suggested goals are tagged at inference time (session_start.py) to distinguish system-inferred from user-created goals
- Delta extraction happens at the hook level (post_tool_use.py) to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence
- Backward compatibility maintained by handling both dict and str goal