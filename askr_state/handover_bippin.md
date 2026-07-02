# Handover: bippin

Last updated: 2026-07-02 16:42

*Source of truth: `handover_bippin.json`*


## Task
Unified all spoken announcements across the askr codebase through a single `announce()` voice pipeline, consolidating duplicated `_speak` helpers and wiring user voice selection into the CLI initialization flow.

## Discussion
The askr voice notification system has evolved from scattered `_speak` helpers in multiple hooks (stop.py, notification.py, pre_compact.py, lifecycle.py) into a unified `announce()` function in voice.py. This session refactored all call sites to route through the single pipeline, added config loaders for prefix and body voices, and integrated voice selection prompts into `askr init`. The two-voice sonic logo (prefix in one voice, body in another) is now consistently applied across all announcement contexts. All 161 tests pass and live playback has been verified.

## Accomplishments
- [x] Refactored duplicated `_speak` helpers from notification.py, pre_compact.py, and lifecycle.py into unified `announce()` function in voice.py
- [x] Added `load_voice_prefix()` and `load_voice_body()` config loaders to askr/state/config.py
- [x] Wired voice selection prompts into `askr init` CLI flow to capture user's prefix and body voice preferences
- [x] Updated all call sites across stop.py, notification.py, pre_compact.py, and lifecycle.py to use `announce()` instead of local `_speak` functions
- [x] Refactored test_voice.py to reflect `announce()` signature and removed tests for obsolete `_speak` variants
- [x] Verified no remaining bare `speak()` imports or calls exist in codebase via grep
- [x] Confirmed live playback of unified announcement pipeline with real macOS say command
- [x] Committed all changes with message 'feat(voice): unify all spoken announcements through one voice pipeline'

## Next Actions
1. Verify that `announce()` correctly handles empty prefix or body strings (should skip that part rather than play silence)
   *Why: Edge case validation to ensure the unified pipeline behaves correctly when caller intentionally omits prefix or body*
2. Test voice selection flow in `askr init` end-to-end with actual user input to confirm config is persisted and loaded on subsequent runs
   *Why: Integration test to verify the CLI wiring works correctly and user preferences survive session boundaries*
3. Document the `announce(text, prefix_text='', prefix_voice='', body_voice='')` signature and voice selection flow in README or ARCHITECTURE.md
   *Why: Future developers need to understand the unified announcement pattern and how to add new announcement contexts*

## Decisions
- All spoken announcements route through a single `announce()` function rather than scattered `_speak` helpers — Single source of truth for voice gating, preconditions, and two-voice pattern; easier to maintain and extend
- Voice selection is captured during `askr init` and persisted in config rather than prompted at runtime — Avoids interrupting the user during normal operation; preferences are set once during setup
- Empty prefix or body strings are valid signals to skip that part of the announcement — Allows callers to use the two-voice pattern selectively without forcing both parts

## Files In Play
- `askr/clients/voice.py`
- `askr/state/config.py`
- `askr/hooks/stop.py`
- `askr/hooks/notification.py`
- `askr/hooks/pre_compact.py`
- `askr/session/lifecycle.py`
- `askr/cli/askr.py`
- `tests/test_voice.py`

## Relational Files
- `askr/state/config.py` (configures): Provides load_voice_enabled(), load_voice_prefix(), load_voice_body() loaders used by voice.py and all hooks
- `tests/test_voice.py` (tested_by): Unit tests for announce() function and voice parameter handling
- `askr/cli/askr.py` (imports): CLI initialization flow now prompts for voice selection and saves to config

## Uncommitted Files
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`
