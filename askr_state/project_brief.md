Last updated: 2026-06-08 22:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or momentum.

## What's In Flight

- Snapshot image generation for test scenarios complete; all 6 scenario cards (stop_auto, stop, context, quota, manual, emergency) generated and sent to Discord for validation
- Emergency checkpoint implementation in progress; needs completion and testing
- Test suite validation pending; recent changes to cost.py, lifecycle.py, and post_tool_use.py need verification

## Key Decisions Made

- State persisted to git as append-only decision log and structured state files (tasks, progress, context snapshots) to enable developer handoffs
- Checkpoint triggered before context auto-compaction and on quota exhaustion; safe interruption validated before pause
- Session lifecycle managed through Claude Code hooks: session_start injects context, user_prompt_submit captures objectives, stop generates handover docs
- Snapshot reporting uses matplotlib for visual scenario validation; Python environment uses system python3 with dotenv from askr venv
- Changes committed without Claude as co-collaborator to maintain clean git history

## Open Goals

- Complete and test