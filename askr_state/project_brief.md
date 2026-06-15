Last updated: 2026-06-16 03:03

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persists state across invocations, and integrates with IDEs and notification systems. It solves the problem of managing long-running, autonomous code generation tasks where the AI needs to maintain context, apply changes to a workspace, validate results, and hand off work across session boundaries.

## What's In Flight

- Multi-project daemon monitoring: refactored daemon loop to track all active projects simultaneously instead of abandoning earlier sessions when new ones start. Root cause was single `last_trigger_at` float; now using per-project dict. Awaiting multi-session test validation.
- Handover system redesign: current checkpoint/goal inference creates stale state when sessions end. Architecture requires rework to defer goal inference until session-end validation and ensure stop checkpoint handler is always invoked.
- Hook payload inspection for delta extraction: moved delta capture to post_tool_use.py hooks rather than checkpoint.py to separate concerns between raw capture and persistence orchestration.

## Key Decisions Made

- Checkpoint format supports both dict and str goal formats for backward compatibility with existing state files while enabling new JSON-serialized format.
- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone; these files control autonomous session continuation.