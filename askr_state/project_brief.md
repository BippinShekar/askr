Last updated: 2026-06-15 13:06

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across checkpoints and supporting autonomous handovers between sessions. It orchestrates subprocess execution, manages conversation history with Claude, and integrates with IDEs to provide context-aware code assistance.

## What's In Flight

- Handover system redesign: checkpoint creation and goal inference timing are broken; stale checkpoints prevent autonomous session continuation. Root cause identified as missing stop checkpoint handler invocation.
- Context checkpoint card display: verifying that "turns remaining" calculation displays correctly in staging before pushing fixes to main.
- Discord webhook integration: env.py and askr.py fixes committed and pushed; awaiting user verification that local .env is now properly read on session startup.

## Key Decisions Made

- Checkpoint goal format accepts both dict and str for backward compatibility with existing state files.
- Delta extraction happens at the hook level (post_tool_use.py), not in checkpoint.py, to separate concerns between raw capture and persistence orchestration.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session from old messages. Auto-inferred goals are tagged at inference time to distinguish them from user-created goals.
- Checkpoint and launch_mode files are the primary handover state carriers; git diffs