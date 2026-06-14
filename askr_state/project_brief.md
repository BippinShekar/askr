Last updated: 2026-06-14 10:02

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across checkpoints and supporting autonomous handovers between sessions. It solves the problem of context loss and manual re-briefing when resuming long-running coding tasks—the agent can pick up where it left off with full session history and goal state.

## What's In Flight

- Analytics redesign: replacing meaningless 'time saved' metric with goal-based or commit-based completion signals. Currently 25% complete; blocked on defining what 'completion' means (user-declared goals, merged commits, or inferred milestones).
- Handover schema stabilization: ensuring checkpoint_pending.json and launch_mode.json correctly carry session state for autonomous continuation. Recent discovery that stop checkpoint handler was never invoked—architectural redesign underway, not incremental fix.
- Context checkpoint card display: verifying 'turns remaining' calculation displays correctly in staging before pushing to main.
- Goal inference timing: shifting from message-aware (mid-session) to session-aware (end-of-session) inference to prevent stale objectives poisoning autonomous handovers.

## Key Decisions Made

- Checkpoint format supports both dict and string goal types for backward compatibility with existing checkpoints while enabling new JSON-serialized format.
- Delta extraction happens at the