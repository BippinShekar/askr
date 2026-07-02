# Handover: bippin

Last updated: 2026-07-02 14:14

*Source of truth: `handover_bippin.json`*


## Task
Fixed a voice announcement gating bug where the per-turn elapsed-time check was mistaking tool_result transcript entries for real user messages, causing session-done announcements to fire incorrectly or not at all.

## Discussion
The voice module's `_turn_elapsed_seconds()` function in `askr/hooks/stop.py` was keying off the last transcript line with `"type": "user"`, but tool_results are also logged under that same type. This caused the gate to measure elapsed time from a tool_result timestamp (often seconds before the actual session end) rather than the last real human message, breaking the per-turn announcement logic. The fix filters out tool_result-shaped entries to find the actual last user message. All 156 tests pass.

## Accomplishments
- [x] Identified root cause of voice announcement timing bug in _turn_elapsed_seconds()
- [x] Fixed entry filter in askr/hooks/stop.py to skip tool_result-shaped user lines
- [x] Added regression test to test_voice.py covering real transcript shape
- [x] Verified all 156 tests pass after fix
- [x] Committed fix to git (99a23e6)

## Files In Play
- `askr/hooks/stop.py`
- `tests/test_voice.py`

## Relational Files
- `tests/test_voice.py` (tested_by): Contains regression test for the _turn_elapsed_seconds fix
