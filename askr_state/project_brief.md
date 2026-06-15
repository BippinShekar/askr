Last updated: 2026-06-15 15:35

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, persistent state, and multi-client support. It orchestrates subprocess execution, maintains conversation history, and bridges agent decisions to actual code modifications through IDE integration.

## What's In Flight

- Roadmap restructuring: Phase 3.12 (Ground-Truth Inference) inserted before Smart Context Injection; all downstream phases renumbered and cross-references fixed. Committed to main.
- Handover system architectural redesign: Current checkpoint timing causes stale goals in autonomous session continuation. Root cause identified as missing stop checkpoint handler invocation.
- Goal inference timing fix: Moving inference from mid-session (message-aware) to session-end validation (session-aware) to prevent objectives from drifting out of sync with actual progress.
- Staging verification pending: Context checkpoint cards must display correct 'turns remaining' before report_image.py fixes are pushed to main.

## Key Decisions Made

- Handover state carriers (checkpoint_pending.json, launch_mode.json) are primary sources of truth for autonomous continuation, not git diffs alone. Investigation revealed these files control session resumption; git state is insufficient.
- Goal inference must be deferred until session-end validation, not auto-inferred mid-session. Auto-inferred goals become stale and