Last updated: 2026-06-15 13:13

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, manages state persistence across sessions, and integrates with local IDEs and Discord for notifications. It solves the problem of context loss and manual handoff friction when working with AI on multi-step coding tasks—the agent remembers where you left off, what you were trying to build, and can resume autonomously or hand off cleanly to a human.

## What's In Flight

- Discord webhook integration during init — user's friend needs to pull latest changes, run `askr init`, and paste their webhook URL when prompted so the project brief posts to Discord on first run
- Checkpoint card display verification in staging — confirming that 'turns remaining' calculation displays correctly in context cards before pushing report_image.py fixes to main
- Handover system architectural redesign — current checkpoint timing is fundamentally broken (stale goals, missed stop handlers); requires rethinking when goals are inferred and how checkpoints are created at session end

## Key Decisions Made

- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone — investigation showed these files control autonomous continuation; git state is insufficient
- Goal inference must be session-aware and deferred to session-end validation, not auto-inferred mid-session from old messages — auto-