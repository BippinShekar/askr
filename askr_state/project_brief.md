Last updated: 2026-06-15 13:48

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client handovers. It bridges your editor, manages conversation history, and can autonomously continue work across sessions when handed over to another user or instance.

## What's In Flight

- Discord webhook initialization flow: fixing `askr init` to prompt for webhook URL, accept it visibly (not hidden), save to `~/.config/askr/.env`, and post project brief to Discord on completion
- Checkpoint card display: verifying that context cards show correct "turns remaining" calculation in staging before pushing to main
- Handover system redesign: addressing root cause of stale checkpoints in autonomous session continuation (goal inference timing and stop checkpoint handler invocation)

## Key Decisions Made

- Treat `checkpoint_pending.json` and `launch_mode.json` as primary handover state carriers; git diffs alone are insufficient for proper session continuation
- Defer goal inference until session-end validation rather than auto-inferring mid-session; prevents stale objectives from poisoning autonomous handovers
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints
- Extract deltas at the hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns
- Skip Discord