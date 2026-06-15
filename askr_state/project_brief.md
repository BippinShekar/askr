Last updated: 2026-06-15 15:27

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with context awareness and usage tracking. It solves the problem of maintaining directive continuity across team handovers — when one developer hands off work to another (or to an autonomous session), the next actor needs clear, actionable next steps derived from explicit user intent, not post-hoc inference from git diffs and transcripts.

## What's In Flight

- Phase 4-1: Task queue system per developer. Goal: enable cross-developer task assignment without requiring users to maintain explicit roadmaps. Currently designing approval gate system (Phase 5) as a prerequisite to prevent privilege escalation when one dev queues tasks under another's session context.
- Team directory restructuring (Phase 4-0): refactoring askr_state/ from flat layout to teams/<team>/members/<dev>/ to support concurrent multi-developer workflows at scale.
- Checkpoint card display verification in staging: confirming 'turns remaining' calculation displays correctly before pushing report_image.py fixes to main.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause is not a race condition but a logic gap where the stop checkpoint handler is never invoked, making handover creation itself fail. This is a fundamental timing issue, not a data formatting problem.
- Goal inference must