Last updated: 2026-06-14 10:09

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, analyzes code context via IDE integration, and hands off work to autonomous agents via structured checkpoints. It solves the problem of context loss and manual re-briefing when developers need to pause, resume, or delegate coding tasks to AI.

## What's In Flight

- Handover data quality fixes: removed emojis and contradictory completion_pct metric from checkpoint output (committed to main)
- Verification of context checkpoint card display in staging to confirm 'turns remaining' calculation is correct after schema changes
- Phase 3.12 roadmap implementation pending (user_rejected_decisions extraction is mostly complete; three Phase 3.11 fixes are pushed)
- Full test suite validation on handover JSON serialization/deserialization after schema removal

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone. These files control autonomous session continuation and are the primary source of truth for resumption.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session from old messages. Auto-inferred goals become stale and poison autonomous handovers.
- Completion tracking uses accomplishments[].done as single source of truth; completion