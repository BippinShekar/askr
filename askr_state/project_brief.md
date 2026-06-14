Last updated: 2026-06-14 09:59

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting autonomous session continuation. It bridges code editors, LLM APIs, and subprocess execution to let users collaborate with AI on coding tasks. The core problem: maintaining coherent session state across interruptions and handoffs so the agent can pick up where it left off without losing context or executing stale goals.

## What's In Flight

- **Stage 3 checkpoint/goal lifecycle completion** — Auto-suggested goals now expire 24 hours after session start (tagged at session_start.py, expired at checkpoint.py). All three stages (stop hook, stale checkpoint gate, goal expiry) are committed to main.
- **Handover format migration audit** — Investigating whether handover.md can be safely deleted in favor of handover.json; need to confirm no fallback logic or dual-file dependencies exist in reader/writer modules.
- **Context checkpoint card verification** — Open goal: confirm 'turns remaining' displays correctly in staging before pushing report_image.py fixes.

## Key Decisions Made

- **Checkpoint and launch_mode.json are primary handover carriers** — Git state alone is insufficient; these files control autonomous session continuation and must be treated as the source of truth for handover state.
- **Goal inference deferred to