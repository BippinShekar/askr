Last updated: 2026-06-14 10:00

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client execution across platforms. It orchestrates code analysis, test execution, and autonomous task completion through a modular architecture centered on session lifecycle management and LLM integration.

## What's In Flight

- Fixing 'time saved' metric in askr status — currently displays wall-clock session duration with no productivity backing. Investigation underway to identify whether outcome tracking (goals completed, context reused, API calls avoided) exists in codebase or needs to be built.
- Verifying checkpoint card display shows correct 'turns remaining' calculation in staging environment before pushing fixes to main.
- Architectural redesign of handover system — current checkpoint persistence is stale at session end due to logic gap where stop checkpoint handler is never invoked. Goal inference must be deferred to session-end validation rather than auto-inferred mid-session.

## Key Decisions Made

- Checkpoint system handles both dict and str goal formats for backward compatibility while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than in checkpoint orchestration — separates concerns cleanly.
- Checkpoint_pending.json and launch_mode.json are primary handover state carriers; git diffs alone are insufficient for proper