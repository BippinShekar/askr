Last updated: 2026-06-15 13:55

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting autonomous handovers to other agents or developers. It manages subprocess execution, maintains conversation history, and integrates with IDEs to provide code context. The core problem it solves: enabling AI agents to pick up mid-session work without losing context or requiring manual state reconstruction.

## What's In Flight

- Fix `.env` loading in askr init so Discord webhook URL auto-loads from repo directory on fresh clones instead of requiring manual re-entry. Currently `load_dotenv()` searches from working directory, not askr package root.
- Verify context checkpoint cards display correct 'turns remaining' calculation in staging environment before pushing report_image.py fixes to main.
- Architectural redesign of handover system to address stale checkpoint issue: goal inference must be deferred to session-end validation rather than auto-inferred mid-session, and stop checkpoint handler invocation must be guaranteed.

## Key Decisions Made

- Checkpoint system treats `checkpoint_pending.json` and `launch_mode.json` as primary handover state carriers, not git diffs alone. Investigation revealed these files control autonomous session continuation.
- Goal inference is session-aware, not message-aware. Auto-inferring from old user messages creates stale objectives that