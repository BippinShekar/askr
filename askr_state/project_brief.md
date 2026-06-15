Last updated: 2026-06-15 14:34

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persists state across runs, and integrates with IDEs and external services like Discord. It solves the problem of maintaining context and continuity in AI-assisted coding workflows, allowing developers to pause and resume sessions without losing progress or conversation history.

## What's In Flight

- Per-project Discord webhook configuration: three-stage implementation complete (config.py, discord.py resolution logic, cmd_init prompt). Staged for commit but git commit command not yet run.
- Checkpoint handover system redesign: root cause identified as missing stop checkpoint handler invocation, not timing issues. Goal inference must be deferred to session-end validation rather than auto-inferred mid-session.
- Context checkpoint card display: verifying that 'turns remaining' calculation displays correctly in staging before pushing report_image.py fixes to main.

## Key Decisions Made

- Checkpoint system handles both dict and str goal formats for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Checkpoint and launch_mode JSON files are primary handover state carriers; git diffs alone are insufficient for proper session continuation