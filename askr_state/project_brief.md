Last updated: 2026-06-15 16:33

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions, tracks token usage, and integrates with IDEs to enable autonomous code work with human oversight. It solves the problem of context loss and manual handoff between AI-assisted coding sessions by persisting session state, inferring next actions from git history, and gating autonomous decisions through human-in-the-loop checkpoints.

## What's In Flight

- Phase 3.12 complete: autonomous session direction inference with HITL confidence gate. Direction is inferred from git log and session arc; when confidence < 0.70, a direction_confirm notification surfaces for human approval before autonomous continuation.
- Verification of context checkpoint cards displaying correct 'turns remaining' in staging environment. Critical for user-facing UX before Phase 3.13.
- End-to-end testing of autonomous handover: trigger session stop, verify direction_confirm notification appears, confirm IDE extension surfaces decision for approval.
- Phase 3.13 planning and dependency assessment once Phase 3.12 verification is complete.

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone. These files control autonomous session continuation; git state is insufficient for proper handover.
- Goal inference is deferred until session-end validation, not auto-