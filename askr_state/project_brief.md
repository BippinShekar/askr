Last updated: 2026-06-15 14:08

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client handoffs. It orchestrates subprocess execution, manages session lifecycle through hooks, and integrates with IDEs and LLM APIs to enable autonomous or human-guided code generation and modification.

## What's In Flight

- Verifying context checkpoint cards display correct 'turns remaining' calculation in staging environment before merging report_image.py fixes to main
- Handover system architectural redesign to fix stale checkpoint creation — root cause identified as missing stop checkpoint handler invocation, not timing issues
- Goal inference refactoring to defer until session-end validation rather than auto-inferring mid-session, preventing stale objectives from poisoning autonomous handovers
- .env loading fix in cmd_init() to load repo .env directly from ASKR_DIR instead of relying on module-level env.load() which was shadowed by ~/.config/askr/.env

## Key Decisions Made

- Checkpoint system treats checkpoint_pending.json and launch_mode.json as primary handover state carriers; git diffs alone are insufficient for proper session continuation
- Delta extraction happens at hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence
-