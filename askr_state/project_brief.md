Last updated: 2026-06-13 22:57

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It orchestrates conversations between users and language models to accomplish coding tasks, maintaining session state across interruptions and enabling autonomous continuation through structured handover documents.

## What's In Flight

- Stage 3 of stop-hook checkpoint refactor: auto-suggested goals are now tagged at session start and expired at checkpoint end to prevent stale objectives from poisoning autonomous handovers. All three stages complete and pushed to main.
- Verification of context checkpoint cards displaying correct "turns remaining" in staging environment (report_image.py calculation).
- Full integration test of goal lifecycle: start session with auto-suggested goals, end session, verify checkpoint creation, start new session and confirm expired goals are absent.
- Phase 3.11 JSON Handover Schema implementation queued as next roadmap item.

## Key Decisions Made

- Stop hook runs first as authoritative checkpoint before any other checkpoint logic, ensuring handover state is captured before session cleanup.
- Checkpoint_pending.json and launch_mode.json are primary handover state carriers; git diffs alone are insufficient for proper session continuation.
- Goal inference is session-aware, not message-aware; auto-inferred goals are tagged at inference time and expire at checkpoint end to prevent stale