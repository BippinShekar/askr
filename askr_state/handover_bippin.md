# Handover: bippin

Last updated: 2026-07-02 17:17

*Source of truth: `handover_bippin.json`*


## Task
Unified all spoken announcements in the voice subsystem through a single `announce()` pipeline, changed the default voice from Samantha to Zarvox, and fixed empty-text handling in the `speak()` function to prevent spurious subprocess calls.

## Discussion
The voice subsystem had multiple entry points for spoken notifications, each using different voice configurations. Prior sessions refactored all call sites to route through a single `announce()` function and changed the default voice to Zarvox per user preference. This session discovered and fixed a bug: `speak_signature()` correctly skipped empty prefix/body strings (per a settled decision), but `speak()` — the path `announce()` uses in single-voice mode — did not guard against empty messages and would call `say ""` anyway. The fix adds an early return in `speak()` when text is empty, and comprehensive tests verify the behavior across all voice modes.

## Accomplishments
- [x] Refactored all spoken announcements to use unified `announce()` pipeline
- [x] Verified all bare `speak()` call sites eliminated and routed through `announce()`
- [x] Changed default single-voice mode from Samantha to Zarvox
- [x] Confirmed test suite passes after voice refactor
- [x] Committed and pushed voice unification (00bd902) and default voice change (80d2625)
- [x] Fixed empty-text handling in `speak()` to skip subprocess call when message is empty
- [x] Added comprehensive tests for empty-string handling in `speak()`, `speak_signature()`, and `announce()`
- [x] Verified full test suite (173 tests) passes after empty-text fix
- [x] Committed and pushed empty-text fix (5a2c3ad)

## Next Actions
1. Test announce() pipeline with all voice types (single-voice Zarvox, dual-voice Good News + Zarvox, signature mode) to verify Zarvox default is applied correctly across all modes
   *Why: Open goal from this session; ensures the Zarvox default works consistently across all voice configurations*
2. Document voice subsystem API changes and migration guide for Zarvox default in README or VOICE_API.md
   *Why: Open goal from this session; helps future developers understand the unified announce() pipeline and voice configuration*

## Decisions
- Default single-voice mode uses Zarvox instead of Samantha — User preference: Samantha sounds too similar to Siri; Zarvox is the preferred default
- All spoken announcements route through unified `announce()` pipeline — Eliminates inconsistent voice configuration across quota warnings, permission prompts, session-done pings, and other notifications
- Empty prefix or body strings are valid signals to skip that part of the announcement — Allows callers to conditionally suppress voice output without special-casing logic; `speak()` and `speak_signature()` both guard against empty text
- `speak()` function skips subprocess call when text is empty — Prevents spurious `say ""` calls that waste system resources; aligns with the settled decision that empty strings are valid skip signals

## User-Rejected Approaches
- **Keep Samantha as the default voice for single-voice mode** — "defaulting to samantha will make it sound like siri, let's default to something else no G, for me zarvox works find as default as well" (domain: askr/state/config.py)

## Files In Play
- `askr/clients/voice.py`
- `askr/hooks/stop.py`
- `askr/hooks/notification.py`
- `askr/state/config.py`
- `tests/test_voice.py`

## Relational Files
- `askr/clients/voice.py` (imported_by): Core voice pipeline; imported by stop.py, notification.py, and other hook modules; fixed empty-text handling in speak() this session
- `askr/hooks/stop.py` (imports): Uses announce() for session-done ping; refactored in prior session
- `askr/hooks/notification.py` (imports): Uses announce() for quota warnings and permission-prompt alerts; refactored in prior session
- `askr/state/config.py` (configures): Defines default voice (VOICE_DEFAULT); changed from Samantha to Zarvox in prior session
- `tests/test_voice.py` (tested_by): Tests voice pipeline; added comprehensive empty-text tests this session; all 173 tests passing

## Uncommitted Files
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`
