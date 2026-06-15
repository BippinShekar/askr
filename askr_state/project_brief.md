Last updated: 2026-06-15 13:11

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with persistent state, event hooks, and notifications. It manages subprocess execution, maintains session checkpoints, and integrates with external LLM APIs and IDEs to enable autonomous or semi-autonomous code generation and iteration.

## What's In Flight

- Fix Discord webhook detection during `askr init` when local .env exists in project directory. Root cause identified: env.load() returns early if global ~/.config/askr/.env exists, preventing local .env from being read. Fix applied to env.py (override=False) and cmd_init (explicit webhook prompt). Awaiting git commit completion and end-to-end verification.
- Verify context checkpoint cards display correct 'turns remaining' in staging environment before pushing report_image.py fixes to main.
- Architectural redesign of handover system to address stale checkpoint and goal inference issues. Current behavior fails when stop checkpoint handler is not invoked; goal inference must be deferred to session-end validation and made session-aware rather than message-aware.

## Key Decisions Made

- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Extract deltas at the hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks