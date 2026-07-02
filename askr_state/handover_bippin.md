# Handover: bippin

Last updated: 2026-07-02 14:25

*Source of truth: `handover_bippin.json`*


## Task
Fixed a voice announcement gating bug where the per-turn elapsed-time check was mistaking tool_result transcript entries for real user messages, causing session-done announcements to fire incorrectly or not at all. Validated the fix end-to-end across multiple scenarios including fast turns, slow turns, and autonomous session relaunches.

## Discussion
The voice module's `_turn_elapsed_seconds()` function in `askr/hooks/stop.py` was keying off the last transcript line with `"type": "user"`, but tool_results are also logged under that same type. This caused the gate to measure elapsed time from a tool_result timestamp (often seconds before the actual session end) rather than the last real human message, breaking the per-turn announcement logic. The fix filters out tool_result-shaped entries to find the actual last user message. This session discovered that `_was_autonomous()` unconditionally imports `askr.session.lifecycle`, which has a module-level side effect that overwrites `os.environ["PATH"]` with a freshly-sourced login-shell PATH. To test the voice announcement behavior end-to-end, a test harness was built that shims `zsh` to return a controlled PATH, allowing the fake `say` command to be injected while keeping real system binaries reachable. All four test scenarios (fast turn silence, slow turn announcement, autonomous relaunch early-return, and multi-turn timing) were verified to work correctly. All 156 tests pass.

## Accomplishments
- [x] Identified root cause of voice announcement timing bug in _turn_elapsed_seconds()
- [x] Fixed entry filter in askr/hooks/stop.py to skip tool_result-shaped user lines
- [x] Added regression test to test_voice.py covering real transcript shape
- [x] Verified all 156 tests pass after fix
- [x] Committed fix to git (99a23e6)
- [x] Discovered PATH clobbering side effect in askr.session.lifecycle module-level import
- [x] Built end-to-end test harness with zsh shim to inject fake say command while preserving system binaries
- [x] Validated voice announcement gating across four scenarios: fast turn (silent), slow turn (announces), autonomous relaunch (early-return), multi-turn timing

## Next Actions
1. Commit the two uncommitted state files (askr_state/goals.jsonl and askr_state/implementation_bippin.jsonl) to persist the new open goals and session history
   *Why: State tracking files have been modified but not yet committed; they need to be saved to git to maintain accurate project history*
2. Implement unit tests for voice announcement gating with tool_result entries (goal a8526cce) — add dedicated test cases to test_voice.py that explicitly cover scenarios where tool_results appear in the transcript
   *Why: Open goal created during session; ensures regression coverage for the tool_result filtering logic*
3. Verify session-done announcement timing across multi-turn conversations (goal 93e0ada1) — run production-like multi-turn sessions and log announcement cadence to confirm no spam on long turns
   *Why: Open goal created during session; validates that the per-turn gate works correctly in realistic multi-turn workflows*

## Decisions
- Filter tool_result-shaped entries (those with 'tool_call_id' or 'tool_name' fields) when searching for the last real user message in _turn_elapsed_seconds() — tool_results are logged under type='user' but represent system responses, not human input; filtering them ensures elapsed time is measured from the actual last human message

## Files In Play
- `askr/hooks/stop.py`
- `tests/test_voice.py`
- `askr/session/lifecycle.py`
- `askr/clients/voice.py`

## Relational Files
- `tests/test_voice.py` (tested_by): Contains regression test for the _turn_elapsed_seconds fix and end-to-end voice announcement scenarios
- `askr/session/lifecycle.py` (imported_by): Module-level import in _was_autonomous() has side effect of overwriting os.environ["PATH"] with login-shell PATH, affecting test harness design
- `askr/clients/voice.py` (configures): Contains speak() and voice announcement logic that depends on correct elapsed-time gating from stop.py

## Uncommitted Files
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`
