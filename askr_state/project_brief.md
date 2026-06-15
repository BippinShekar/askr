Last updated: 2026-06-15 16:38

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across invocations and supporting autonomous session continuation. It bridges user intent, LLM reasoning, and local code changes through a session lifecycle that tracks direction (what the user is trying to accomplish), validates progress, and hands off work to autonomous agents when the user steps away.

## What's In Flight

- Direction inference system (Phase 3.13): Three-signal detection (blockers.md, git momentum, checkpoint card) to infer session goals automatically. Recently fixed signal parsing bugs; now stress-testing under high-volume scenarios before HITL validation gate.
- Checkpoint handover mechanism: Captures session state at end-of-session for autonomous continuation. Currently validating that checkpoint cards display correct metadata (turns remaining, inferred goals) in staging.
- Notification system: direction_confirm gate fires when inference confidence drops below 0.70, prompting user validation before autonomous handoff.

## Key Decisions Made

- Goal inference is session-aware, not message-aware. Auto-inferred goals are tagged at session start (session_start.py) to distinguish system suggestions from user-created goals; prevents stale objectives from poisoning autonomous handovers.
- Checkpoint and launch_mode.json are primary handover state carriers. Git diffs alone