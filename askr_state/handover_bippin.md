# Handover: bippin

Last updated: 2026-07-02 14:09

*Source of truth: `handover_bippin.json`*


## Task
Fixed the per-turn elapsed-time gate in the session-done ping by correcting the user-message detection logic to skip tool_result entries, restoring the announcement behavior for auto-started sessions.

## Discussion
The askr voice notification system has progressively hardened over recent sessions with emergency kill announcements, humanized spoken text, and per-turn elapsed-time gating for the session-done ping. In the previous session, the gating logic was decoupled and tested, but production observation revealed the gate almost never fired because `_turn_elapsed_seconds` was mistakenly treating tool_result-shaped entries as real user messages, preventing the elapsed-time calculation from working correctly. This session identified and fixed the entry filter to skip tool_result lines, added a regression test using real transcript shapes, verified all 26 voice tests and 156 full suite tests pass, and committed the fix.

## Accomplishments
- [x] Identified bug in _turn_elapsed_seconds: was not filtering out tool_result entries when finding last user message
- [x] Fixed entry filter in askr/hooks/stop.py to skip tool_result-shaped user lines
- [x] Added regression test in tests/test_voice.py using real transcript shape with tool_result entries
- [x] Verified all 26 voice tests pass (25 original + 1 new regression test)
- [x] Verified full test suite (156 tests) passes
- [x] Committed and pushed fix (commit 99a23e6)

## Next Actions
1. Verify in production that the session-done ping now fires correctly for auto-started sessions and respects the per-turn elapsed-time gate
   *Why: The bug fix restores the announcement behavior; production observation will confirm the gate now works as intended*
2. Monitor whether the per-turn gate suppresses spam on long-running turns and adjust the elapsed-time threshold if needed
   *Why: Real-world behavior will validate the heuristic and inform any tuning required*

## Decisions
- Gate the session-done ping on per-turn elapsed time, not session total — Prevents spam on long-running sessions by only speaking 'done' when a single turn has taken sufficient time
- Decouple the Discord card's gate logic from its call site — Improves separation of concerns and makes the gating logic testable and reusable
- Filter out tool_result entries when detecting the last real user message for elapsed-time calculation — Tool results are not user messages and should not reset the elapsed-time clock; only actual user input should count

## Failed Approaches
- Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire

## Files In Play
- `askr/hooks/stop.py`
- `tests/test_voice.py`

## Relational Files
- `askr/voice.py` (imported_by): Contains the speak() function and voice notification logic that stop.py gates
- `tests/test_voice.py` (tests): Tests the voice notification system including the per-turn gating logic and real transcript shapes

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
