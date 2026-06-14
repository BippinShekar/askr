Last updated: 2026-06-14 10:18

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM to analyze code, suggest changes, and track progress. It manages session state, integrates with IDEs to read and modify files, and hands off work to autonomous agents via structured checkpoint files. The core problem it solves: enabling developers to delegate coding tasks to AI while maintaining continuity across sessions and preventing repeated work.

## What's In Flight

- Fixing handover task field semantics: tasks are currently written imperatively ("Remove emojis") causing autonomous sessions to re-read completed work as pending. Need to switch to past-tense descriptive form ("Removed emojis from X").
- Investigating next_actions generation logic in the stop hook to confirm it derives from accomplishments and git state, not from the task field itself (which would create a repetition loop).
- Verifying context checkpoint cards display correct "turns remaining" calculation in staging before pushing to main.
- Decoupling task field content from next_actions generation so autonomous sessions don't burn tokens re-doing completed work.

## Key Decisions Made

- Checkpoint and handover files (checkpoint_pending.json, launch_mode.json, handover.md) are the primary state carriers for session continuation—git diffs alone are insufficient.
- Goal inference must be session-aware and deferred until session