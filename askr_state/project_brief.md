Last updated: 2026-06-13 23:05

# Project Brief

Askr is a CLI-based AI coding agent that manages long-running development sessions with Claude by persisting context, tracking token usage, and enabling seamless handoffs between human and autonomous work. It solves the problem of Claude sessions timing out or losing context mid-task by checkpointing progress and resuming from a known state.

## What's In Flight

- Handover system redesign: root cause identified (stop checkpoint handler never invoked); requires architectural fix to defer goal inference until session-end validation rather than mid-session auto-inference
- Context checkpoint card display: verifying 'turns remaining' calculation displays correctly in staging before pushing to main
- Pre-launch Twitter/X strategy: building audience through replies to @lachygroom, @swyx, @levelsio, @marc_louvion on Claude context/session management topics (3-5 days of staggered replies, then launch thread in ~1 week)
- README polish: landing page for Twitter click-through traffic needs final review before public launch

## Key Decisions Made

- Checkpoint system treats checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone—investigation revealed these files control autonomous continuation
- Goal inference must be session-aware and deferred to session-end validation, not auto-inferred from old user messages mid-session—