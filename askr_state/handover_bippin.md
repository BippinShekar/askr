# Handover: bippin

Last updated: 2026-07-02 16:31

*Source of truth: `handover_bippin.json`*


## Task
Implemented dual-voice 'sonic logo' for session-done notifications and added voice parameter support to the speak() function.

## Discussion
The askr voice notification system has been extended to support per-call voice selection and a two-voice signature pattern for the session-done ping. The 'Done.' prefix now plays in one voice (askr's branded prefix voice) followed by the detail in a second, distinct voice, creating a recognizable sonic logo that differentiates askr's notifications from generic TTS. The implementation refactored preconditions into a shared gate, added voice parameter to speak(), introduced speak_signature() for the two-tone pattern, and updated the done-ping logic to use random phrases when no goals are completed. All 161 tests pass.

## Accomplishments
- [x] Added voice parameter to speak(text, voice='') to support per-call voice selection via macOS -v flag
- [x] Implemented speak_signature(prefix, body, prefix_voice, body_voice) for two-voice sequential playback
- [x] Refactored voice preconditions into shared _say_preconditions() gate used by both speak() and speak_signature()
- [x] Updated _speak_session_done() to use speak_signature() with configurable prefix and body voices
- [x] Added _GENERIC_DONE_PHRASES rotation for no-goal case to vary the detail portion of the done ping
- [x] Added test coverage for speak_signature() and voice parameter in test_voice.py
- [x] Verified live playback through actual code path with real macOS say command
- [x] All 161 tests passing (156 prior + 5 new)

## Next Actions
1. Commit the voice.py and stop.py changes with message 'feat(voice): dual-voice sonic logo for session-done ping'
   *Why: Changes are complete, tested, and verified live; ready for permanent record*
2. Verify that load_voice_prefix() and load_voice_body() config keys exist in askr/state/config.py or add them if missing
   *Why: The stop.py code references these config loaders; they must be present for the feature to work end-to-end*

## Decisions
- Two-voice pattern uses sequential subprocess.run() calls rather than a single say command with multiple -v flags — macOS say does not support switching voices mid-utterance; sequential calls with brief natural pause between them create the desired effect
- Preconditions gate (voice_notifications on, macOS, say on PATH) is shared via _say_preconditions() rather than duplicated — Single source of truth for the gating logic; both speak() and speak_signature() must pass the same checks
- speak_signature() always fires both prefix and body if preconditions pass, even if one is empty string — Allows caller to control whether prefix is spoken; empty string is a valid 'skip this part' signal
- Generic done phrases are rotated randomly rather than cycling through a fixed sequence — Prevents predictable repetition; user hears variety across multiple sessions

## Files In Play
- `askr/clients/voice.py`
- `askr/hooks/stop.py`
- `tests/test_voice.py`

## Relational Files
- `askr/state/config.py` (configures): Provides load_voice_enabled(), load_voice_prefix(), load_voice_body() config loaders used by voice.py and stop.py
- `tests/test_voice.py` (tested_by): Contains 5 new test cases for speak_signature() and voice parameter; all 31 voice tests pass
