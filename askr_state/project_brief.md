Last updated: 2026-06-14 14:29

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It solves the problem of broken cross-team handover: when one developer hands off work to another (or to an autonomous session), the LLM-generated next_actions are inferred from code diffs and transcripts, not from user intent or team goals, causing autonomous sessions to re-execute completed work and waste tokens.

## What's In Flight

- Fixing checkpoint prompt to generate task descriptions as past-tense outcomes ("Removed emojis") instead of imperative directives ("Remove emojis"), preventing autonomous re-execution of completed work.
- Extending checkpoint prompt to inject open_goals.md and team_context.md into next_actions generation, grounding handover in intentional team dependencies rather than local file diffs.
- Adding validation in create_checkpoint() to reject next_actions that match completed accomplishments (fuzzy match), catching LLM hallucinations.
- Stress-testing end-to-end: create a handover.md, start an autonomous session, verify it does NOT re-execute the previous session's task.
- Verifying context checkpoint cards display correct 'turns remaining' in staging before pushing report_image.py fixes.

## Key Decisions Made

- Checkpoint