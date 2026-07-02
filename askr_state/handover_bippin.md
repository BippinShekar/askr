# Handover: bippin

Last updated: 2026-07-02 16:31

*Source of truth: `handover_bippin.json`*


## Task
Implemented a two-voice sonic logo for session-done announcements by refactoring the voice module to support per-voice control, adding a `speak_signature()` function that plays a branded 'Done.' prefix in one voice followed by contextual detail in a second voice, and integrated it into the stop hook with randomized generic phrases for no-goal sessions.

## Discussion
This session extended the voice announcement system beyond single-voice TTS to support askr's distinctive two-tone notification pattern. The refactor extracted shared preconditions (`_say_preconditions()`) to avoid duplication, added a `voice=` parameter to `speak()` for single-voice calls, and introduced `speak_signature(prefix, body, prefix_voice, body_voice)` for the branded done ping. The stop hook was updated to call `speak_signature("Done.", body, load_voice_prefix(), load_voice_body())` where body is either the first completed goal or a randomly-selected generic phrase when no goals completed but the turn ran long enough. All 161 tests pass (156 prior + 5 new covering the two-voice signature). The implementation was validated live through the actual code path using the project's venv Python interpreter.

## Accomplishments
- [x] Identified root cause of voice announcement timing bug in _turn_elapsed_seconds()
- [x] Fixed entry filter in askr/hooks/stop.py to skip tool_result-shaped user lines
- [x] Added regression test to test_voice.py covering real transcript shape
- [x] Verified all 156 tests pass after fix
- [x] Committed fix to git (99a23e6)
- [x] Discovered PATH clobbering side effect in askr.session.lifecycle module-level import
- [x] Built end-to-end test harness with zsh shim to inject fake say command while preserving system binaries
- [x] Validated voice announcement gating across four scenarios: fast turn (silent), slow turn (announces), autonomous relaunch (early-return), multi-turn timing
- [x] Refactored voice.py to extract shared preconditions into _say_preconditions()
- [x] Added voice= parameter to speak() function for per-voice control
- [x] Implemented speak_signature(prefix, body, prefix_voice, body_voice) for two-voice sonic logo
- [x] Added _GENERIC_DONE_PHRASES rotation for no-goal session-done announcements
- [x] Updated _speak_session_done() to use speak_signature() with voice config loaders
- [x] Added 5 new test cases to test_voice.py covering speak_signature and voice parameter
- [x] Verified all 161 tests pass (156 prior + 5 new)
- [x] Validated live voice announcement through actual code path using venv Python

## Next Actions
1. Commit all five uncommitted files (askr/clients/voice.py, askr/hooks/stop.py, askr/state/config.py, tests/test_voice.py, askr_state/implementation_bippin.jsonl) to persist the two-voice sonic logo implementation
   *Why: Core feature implementation is complete and tested; changes must be committed to git to preserve work*
2. Verify that load_voice_prefix() and load_voice_body() config loaders exist and return valid macOS voice names (e.g. 'Good News', 'Zarvox'); add them to askr/state/config.py if missing
   *Why: The speak_signature() call in stop.py depends on these config loaders; they must be implemented for the feature to work in production*
3. Test the two-voice sonic logo in a real multi-turn session to confirm the 'Done.' prefix and detail play sequentially without overlap and sound distinct
   *Why: Live validation ensures the user experience matches the design intent of a recognizable branded notification*
4. Implement unit tests for voice announcement gating with tool_result entries (goal a8526cce) — add dedicated test cases to test_voice.py that explicitly cover scenarios where tool_results appear in the transcript
   *Why: Open goal from prior session; ensures regression coverage for the tool_result filtering logic*
5. Verify session-done announcement timing across multi-turn conversations (goal 93e0ada1) — run production-like multi-turn sessions and log announcement cadence to confirm no spam on long turns
   *Why: Open goal from prior session; validates that the per-turn gate works correctly in realistic multi-turn workflows*

## Decisions
- Filter tool_result-shaped entries (those with 'tool_call_id' or 'tool_name' fields) when searching for the last real user message in _turn_elapsed_seconds() — tool_results are logged under type='user' but represent system responses, not human input; filtering ensures the elapsed-time gate measures from the actual last user message
- Implement two-voice sonic logo for session-done announcements: a short branded 'Done.' prefix in one voice followed by contextual detail in a second voice — Distinguishes askr's done notification from generic TTS alerts; the constant prefix is recognizable while the detail voice adds variety and prevents monotony
- Use randomized generic phrases (_GENERIC_DONE_PHRASES) for no-goal sessions instead of a single 'Done.' message — Prevents the notification from sounding identical every time; maintains the branded prefix while varying the detail to keep the user experience fresh
- Extract shared preconditions (voice_enabled check, macOS gate, say binary lookup) into _say_preconditions() helper — Eliminates duplication between speak() and speak_signature(); both functions need identical gating logic
- Add voice= parameter to speak() function with empty string default for system default voice — Allows single-voice calls to specify a particular macOS voice when needed; backward-compatible with existing code that omits the parameter

## Files In Play
- `askr/clients/voice.py`
- `askr/hooks/stop.py`
- `askr/state/config.py`
- `tests/test_voice.py`

## Relational Files
- `askr/state/config.py` (imported_by): stop.py calls load_voice_prefix() and load_voice_body() from config; these loaders must return valid macOS voice names
- `tests/test_voice.py` (tested_by): Contains unit tests for speak(), speak_signature(), and _say_preconditions(); validates the two-voice implementation
- `askr/hooks/stop.py` (imports): Calls speak_signature() from voice.py to announce session completion with the two-voice sonic logo

## Uncommitted Files
- `askr/clients/voice.py`
- `askr/hooks/stop.py`
- `askr/state/config.py`
- `askr_state/implementation_bippin.jsonl`
- `tests/test_voice.py`

## Blockers
- load_voice_prefix() and load_voice_body() config loaders must be implemented in askr/state/config.py before the two-voice sonic logo can run in production
