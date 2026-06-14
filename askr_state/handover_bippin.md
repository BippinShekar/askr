# Handover: bippin

Last updated: 2026-06-14 14:29

*Source of truth: `handover_bippin.json`*


## Task
Diagnose and fix the architectural flaw where next_actions inferred from LLM checkpoints don't align with actual user intent, causing token waste and broken cross-team handover utility.

## Discussion
The session exposed a critical gap: `completion_pct` was removed from the schema, but the real problem is deeper—the LLM generates `next_actions[]` based on transcript + git state, not on user intent or cross-team context. An autonomous session reading handover.md will see imperative task descriptions ("Remove emojis") instead of past-tense outcomes, causing it to re-execute completed work. Building 3.12 alone won't fix this; the checkpoint prompt itself needs to ground next_actions in user goals and team dependencies, not just file diffs. Without that, askr remains a session-local tool, not a cross-team handover system.

## Accomplishments
- [x] Removed `completion_pct` from writer.py, reader.py, and checkpoint.py LLM prompt
- [x] Converted handover markdown emoji rendering from ✅/🔲 to [x]/[ ]
- [x] Identified root cause: task field is imperative, not descriptive; next_actions are inferred from diffs, not user intent
- [x] Exposed that autonomous sessions will re-execute completed work if handover task descriptions remain directive

## Next Actions
1. Rewrite checkpoint.py prompt to generate task as past-tense outcome ("Removed emojis from handover.md") not imperative directive ("Remove emojis from..."). Add explicit instruction: 'Describe what was accomplished, not what should be done.'
   *Why: Prevents autonomous sessions from re-executing completed work. This is the immediate token-waste blocker.*
2. Extend checkpoint prompt to inject open_goals.md and team_context.md (if exists) into next_actions generation. Instruct LLM: 'Ground next_actions in unmet user goals and cross-team dependencies, not just file diffs.'
   *Why: Transforms next_actions from local-session inference to intentional cross-team handover. Addresses the architectural flaw that makes askr unuseful for multi-developer workflows.*
3. Add validation in create_checkpoint(): if a next_action matches a completed accomplishment (fuzzy string match), reject it and regenerate that action.
   *Why: Safety net to catch LLM hallucinations where it proposes work already done in the same session.*
4. Before building 3.12, run a stress test: create a handover.md, start a new autonomous session, verify it does NOT re-execute the task from the previous session's accomplishments.
   *Why: Validates the fix works end-to-end before shipping. Prevents shipping a tool that burns tokens on repeated work.*
5. Document in README: 'askr is designed for cross-team handover. Each session reads the previous handover.md and builds on it. Task descriptions are outcomes, not directives. Next actions are grounded in team goals, not just code diffs.'
   *Why: Sets user expectations. Clarifies that askr is not a session-local tool; it's a multi-developer coordination system.*

## Decisions
- Do NOT build 3.12 until checkpoint prompt is rewritten to ground next_actions in user intent, not file diffs. — Building 3.12 without fixing the prompt will ship a tool that causes autonomous sessions to re-execute completed work, wasting tokens and breaking cross-team utility. The architectural flaw is in the prompt, not the schema.
- Task field must be past-tense outcome, not imperative directive. — Autonomous sessions will treat imperative directives as new work to do, causing repetition. Past-tense signals 'this is done; move on.'

## User-Rejected Approaches
- **Building 3.12 as the next step to improve handover quality.** — "how will building the 3.12 help with this problem... if our inferred next steps in handover aren't really in-tune then how would askr ever be useful for the user for the user's cross-team functionality. be brutally honest." (domain: roadmap.md / architecture)

## Failed Approaches
- Removing `completion_pct` from the schema as the primary fix for handover accuracy. — It addressed a symptom (contradictory metrics) but not the root cause: next_actions are inferred from git diffs and transcript, not from user intent or team goals. The LLM still generates directives instead of outcomes.
- Assuming that once next_actions are generated, an autonomous session will correctly interpret them as 'things to do next' rather than 'things that were already done.' — Imperative task descriptions ('Remove emojis') read as new work, not completed work. The handover format itself is ambiguous to downstream sessions.

## Files In Play
- `askr/state/writer.py`
- `askr/state/reader.py`
- `askr/session/checkpoint.py`
- `roadmap.md`

## Relational Files
- `askr/session/checkpoint.py` (configures): Contains the LLM prompt that generates next_actions. This is where the architectural flaw lives.
- `goals.md` (imported_by): Should be injected into checkpoint prompt to ground next_actions in user intent, not just diffs.
- `roadmap.md` (configures): Phase 4 was removed this session. Clarifies that 3.12 is pre-launch, not post-launch work.

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`

## Blockers
- Checkpoint prompt generates imperative task descriptions instead of past-tense outcomes, causing autonomous sessions to re-execute completed work.
- Next_actions are inferred from git diffs and transcript, not grounded in user goals or team context. This breaks cross-team handover utility.
