Last updated: 2026-06-15 19:09

# Project Brief

Askr is a CLI-based AI coding agent that manages user sessions, handles notifications, and integrates with IDE environments for code analysis and assistance. It solves the problem of maintaining context and direction across multi-turn coding sessions, particularly when handing off work to autonomous continuation or returning developers.

## What's In Flight

- Intent detection for research-only sessions: adding logic to distinguish between research that concludes with implementation direction vs. exploratory research without actionable next steps. Currently designing Signal 3 extension to carry `intent_detected` flag alongside `proposed` flag.
- Three-way notification routing for session handover: context (auto-continue for coding sessions), direction_proposal (research with intent), and no_direction fallback (research without intent or fallback to prior coding session).
- End-to-end testing of autonomous continuation logic across three scenarios: research + implementation signal, research + no signal, and research + fallback to prior context.

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone. These files control autonomous session continuation and are the primary source of truth for session resumption.
- Goal inference is deferred to session-end validation, not auto-inferred mid-session. This prevents stale objectives from poisoning autonomous handovers.
- Goals inferred by the