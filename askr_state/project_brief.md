Last updated: 2026-06-14 10:01

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It enables developers to collaborate with AI on code generation and modification through a stateful, resumable session model backed by local filesystem storage and provider APIs.

## What's In Flight

- Phase 3 (auto-suggested goals expiry): Complete. Goals are now tagged at inference time, validated at session end, and expired via checkpoint. All three stages committed to main.
- Phase 3.12: Pending scope review from roadmap.md before kickoff.
- Verification task: Confirm context checkpoint cards display correct 'turns remaining' in staging environment.
- Uncommitted state: askr_state/implementation_state.md, roadmap.md, and stress-tests/ need to be staged before Phase 3.12 begins.

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone. These files control autonomous session continuation and are the primary source of truth for resumption.
- Goal inference is session-aware, not message-aware. Auto-inferred goals are tagged at session_start.py to distinguish them from user-created goals and prevent stale objectives from poisoning autonomous handovers.
- Goal expiry happens