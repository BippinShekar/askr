Last updated: 2026-06-13 23:15

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with Claude, solving the friction of context loss across sessions, machine switching overhead, and handoff explanation burden. It persists conversation history and execution context locally, integrates with your IDE, and coordinates with LLM APIs to maintain continuity in long-running coding tasks.

## What's In Flight

- Handover system redesign: root cause identified (stop checkpoint handler never invoked); goal inference must be deferred to session-end validation rather than auto-inferred mid-session to prevent stale objectives in autonomous handovers
- Staging verification of checkpoint card display for correct 'turns remaining' calculation before main branch push
- Twitter/X launch positioning: sarcasm-led teaser tweet (75% complete) highlighting Claude friction points without revealing product; 10 high-signal accounts identified for organic reach (@alexalbert__, @simonw, @swyx, @karpathy, etc.)
- Public launch in ~7 days; GitHub launch thread and README GIFs pending

## Key Decisions Made

- Checkpoint system treats `checkpoint_pending.json` and `launch_mode.json` as primary handover state carriers, not git diffs alone—investigation revealed these files control autonomous session continuation
- Goal inference deferred to session-end validation, not auto-inferred mid-