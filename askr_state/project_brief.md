Last updated: 2026-06-15 18:18

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions in VSCode, analyzing code and maintaining persistent state across handovers. It solves the problem of context loss and token wastage when autonomous sessions need to resume or hand off to humans—by capturing session state, inferring direction, and gating continuation on human confirmation when confidence is low.

## What's In Flight

- Direction confirmation gate (Signal 4 path): Implemented handler in stop.py and extension.js to block autonomous session resumption when handover inference confidence falls below 0.70; requires human input via VSCode input box instead of auto-opening session.
- Testing direction_confirm UX in VSCode: Verify that stale/empty handover triggers input prompt and blocks auto-session correctly.
- Adoption strategy inference: User signaled readiness to explore product direction around virality and downloads; next autonomous session should populate handover.next_actions with 3-5 adoption-focused actions.
- Documentation gap: Signal paths (Signal 3 normal flow, Signal 4 edge case, Signal 5 zero-direction) and token implications not yet documented; lifecycle.md or README needs clarity.

## Key Decisions Made

- Handover.json always exists in normal operation, so Signal 3 (fresh handover) is the default path and Signal 4 