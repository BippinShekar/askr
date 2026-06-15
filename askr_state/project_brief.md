Last updated: 2026-06-15 18:25

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and hooking into your IDE to apply code changes. It solves the problem of context loss in multi-turn coding workflows—you can pause a session, come back later, and the agent picks up exactly where it left off with full conversation history and file state.

## What's In Flight

- **Signal 3 direction inference** — Implemented git-history-based detection to route returning sessions to either autonomous continuation or conversation mode. Walks handover commit history to find the last actual coding session, avoiding false positives from timestamp-based staleness checks.
- **End-to-end direction_confirm flow** — Testing the full pipeline: Signal 3 triggers, user sees input box, selects direction, autonomous session opens. Needs validation with rapid session cycles (talk → code → talk → code).
- **Session log finalization** — `askr_state/implementation_state.md` accumulating tool runs and edits; needs final commit before next handover.

## Key Decisions Made

- **Handover state lives in checkpoint_pending.json and launch_mode.json**, not git diffs alone. These files control autonomous session continuation; git state is insufficient for proper handover.
- **Goal inference deferred to session-end validation