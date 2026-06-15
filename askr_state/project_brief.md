Last updated: 2026-06-15 13:04

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client handovers. It bridges code editors, manages subprocess execution, and coordinates with external AI services to assist developers in real-time coding tasks.

## What's In Flight

- Discord webhook initialization: fixed send failure detection and env.load() merge order so local .env vars are properly picked up after global config
- Checkpoint card display: verifying "turns remaining" calculation displays correctly in staging before pushing report_image.py fixes
- Handover system redesign: architectural work to fix stale checkpoint issue where goal inference happens mid-session instead of at session-end validation

## Key Decisions Made

- Checkpoint and launch_mode.json are primary handover state carriers, not git diffs alone — investigation showed these files control autonomous session continuation
- Goal inference deferred to session-end validation, not auto-inferred mid-session — auto-inference from old messages creates stale objectives that poison autonomous handovers
- Delta extraction happens at hook level (post_tool_use.py) not checkpoint.py — separates concerns between raw capture and persistence orchestration
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON format
- Discord success message gates on both sent AND brief flags —