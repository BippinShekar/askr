Last updated: 2026-06-13 22:17

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive sessions with Claude, tracks API costs and token usage, and integrates with IDEs and notification systems. It solves the problem of coordinating long-running AI-assisted coding tasks by maintaining session state, managing context windows, and providing visibility into resource consumption across multiple invocations.

## What's In Flight

- Investigating missing cost display in `askr init` command. Root cause not yet identified; requires tracing cost calculation flow from CLI entry through API calls to output formatting.
- Verifying checkpoint card display shows correct "turns remaining" calculation in staging environment before pushing fixes to main.
- Fixing `report_image.py` to correctly calculate turns-until-auto-compact using existing `cost_summary` data rather than adding new fields.

## Key Decisions Made

- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Implement delta extraction at the hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers; git diffs alone are insufficient for proper autonomous session continuation.
- Focus on hook payload inspection rather than reverse-engineering the