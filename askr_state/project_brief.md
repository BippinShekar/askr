Last updated: 2026-06-13 22:14

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive sessions with an LLM, tracks token usage, and integrates with IDEs and notification systems. It solves the problem of maintaining context across long coding sessions by persisting session state, calculating remaining context windows, and automatically compacting conversations when approaching token limits.

## What's In Flight

- Verifying context checkpoint card display logic for "turns remaining" calculation in staging environment. The turns-until-auto-compact metric must match the logic in report_image.py.
- Committing phase 3.11 changes to checkpoint verification and handover consistency mechanisms (checkpoint_pending.json and launch_mode.json).
- Pushing report_image.py fixes for turns-until-auto-compact calculation to main branch.
- Investigating divergence between main repo and leaps repo in how askr_init generates handover state files and checkpoint mechanisms.

## Key Decisions Made

- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Implement delta extraction at the hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Focus on hook payload inspection rather than reverse-engineering the binary compaction algorithm; payloads are more