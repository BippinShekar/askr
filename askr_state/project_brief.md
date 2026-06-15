Last updated: 2026-06-15 17:42

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, persistent state, and multi-client support. It bridges developer intent with autonomous code execution by maintaining session context across CLI invocations, inferring work direction from git history and dirty files, and handing off to autonomous agents when appropriate.

## What's In Flight

- Direction inference engine: Replaced root-folder momentum (Signal 3) with semantic commit-scope analysis to eliminate false-positive gate clearances. All three signals (dirty files, handover next_actions, commit scopes) validated in isolation; full chain integration pending.
- End-to-end direction inference test: Verify three-signal chain produces correct direction without HITL gate in fresh session start.
- Edge case stress testing: Empty git log, no conventional commits, multi-scope dirty files, and other robustness scenarios.
- Handover prompt documentation: Update _generate_handover_prompt() to explain three-signal model and confidence thresholds (0.95 dirty, 0.85 handover, 0.65 semantic scope).
- HITL gate validation: Confirm direction_confirm triggers only when max(signal_confidences) < 0.70 and surfaces competing signals correctly.

## Key Decisions Made

- Handover system requires architectural redesign, not