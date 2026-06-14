# Handover: bippin

Last updated: 2026-06-14 10:18

*Source of truth: `handover_bippin.json`*


## Task
Investigate why next_actions list generation in stop hook may create task repetition when handover.md is read by autonomous session, and clarify task field semantics (imperative vs. descriptive).

## Discussion
Session identified two interconnected issues: (1) handover.md task field is written imperatively ('Remove emojis...') instead of descriptively ('Removed emojis...'), causing autonomous sessions to re-read completed work as pending tasks; (2) next_actions list generation logic in stop hook was not yet examined — user asked what basis it uses to create next actions, implying concern that it may derive from task field rather than accomplishments or git state. Emojis and completion_pct metric were successfully removed in prior work. Session ended mid-investigation into stop hook behavior.

## Accomplishments
- [x] Removed emoji characters (✅, 🔲, ✓) from handover markdown renderer in writer.py
- [x] Eliminated completion_pct metric from LLM prompt schema, context injection, and markdown output
- [x] Identified task field semantics problem: imperative language causes autonomous re-reads to treat completed work as pending

## In Progress
- `askr/session/checkpoint.py`: Investigating stop hook's next_actions generation logic and its dependency chain (whether it reads task field, accomplishments, or git state)

## Next Actions
1. Locate and read the stop hook implementation that generates next_actions list — grep for 'next_actions' or 'next_action' in checkpoint.py and session/ directory
   *Why: User asked what basis next_actions uses; need to verify it doesn't derive from task field (which would create repetition loop)*
2. Change task field prompt in checkpoint.py from imperative ('Remove X') to past-tense descriptive ('Removed X from Y')
   *Why: Prevents autonomous sessions from re-reading completed accomplishments as pending work*
3. Verify next_actions generation uses accomplishments[].done and git diff as sources, NOT task field
   *Why: Ensures autonomous session won't repeat work already marked done in accomplishments array*
4. Test: create a handover with completed accomplishment, run autonomous session, verify it does not re-add that work to next_actions
   *Why: Confirm the repetition fallacy is prevented before moving to 3.12 build*
5. Commit changes to writer.py, reader.py, checkpoint.py once task field semantics are fixed
   *Why: Current commit only removed completion_pct; task field fix is still pending*

## Decisions
- Task field must be written in past-tense descriptive form, not imperative — Autonomous sessions read handover.md and interpret imperative task as work-to-do, creating token-burning repetition of completed work
- next_actions generation must be decoupled from task field content — Task field is for human context; next_actions should derive from accomplishments.done status and git state only

## Failed Approaches
- Writing task field as imperative directive ('Remove emojis from...') — Autonomous sessions misinterpret it as pending work, causing repetition and wasted tokens on verification

## Files In Play
- `askr/session/checkpoint.py`
- `askr/state/writer.py`
- `askr/state/reader.py`

## Relational Files
- `askr/session/checkpoint.py` (configures): Contains LLM prompt that generates task field and next_actions; stop hook logic resides here
- `askr/state/writer.py` (imported_by): Renders handover.md from JSON; task field semantics affect how autonomous sessions interpret output
- `askr/state/reader.py` (imported_by): Parses handover.md back into state; must handle task field correctly to avoid repetition

## Uncommitted Files
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Stop hook next_actions generation logic not yet examined — need to confirm it doesn't depend on task field
