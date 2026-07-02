# Handover: bippin

Last updated: 2026-07-02 17:13

*Source of truth: `handover_bippin.json`*


## Task
Unified all spoken announcements in the voice subsystem through a single `announce()` pipeline and changed the default voice from Samantha to Zarvox.

## Discussion
The voice subsystem had multiple entry points for spoken notifications (quota warnings, permission prompts, session-done pings, etc.), each using different voice configurations. This session refactored all call sites to route through a single `announce()` function, eliminating the bare `speak()` import pattern. The user rejected Samantha as the default voice (citing similarity to Siri) and requested Zarvox instead, which was applied to single-voice mode while preserving the existing dual-mode behavior (Good News prefix + Zarvox body).

## Accomplishments
- [x] Refactored all spoken announcements to use unified `announce()` pipeline
- [x] Verified all bare `speak()` call sites eliminated and routed through `announce()`
- [x] Changed default single-voice mode from Samantha to Zarvox
- [x] Confirmed test suite passes after voice refactor
- [x] Committed and pushed voice unification (00bd902) and default voice change (80d2625)

## Decisions
- Default single-voice mode uses Zarvox instead of Samantha — User preference: Samantha sounds too similar to Siri; Zarvox is the preferred default
- All spoken announcements route through unified `announce()` pipeline — Eliminates inconsistent voice configuration across quota warnings, permission prompts, session-done pings, and other notifications

## User-Rejected Approaches
- **Keep Samantha as the default voice for single-voice mode** — "defaulting to samantha will make it sound like siri, let's default to something else no G, for me zarvox works find as default as well" (domain: askr/state/config.py)

## Files In Play
- `askr/clients/voice.py`
- `askr/hooks/stop.py`
- `askr/hooks/notification.py`
- `askr/state/config.py`
- `tests/test_voice.py`

## Relational Files
- `askr/clients/voice.py` (imported_by): Core voice pipeline; imported by stop.py, notification.py, and other hook modules
- `askr/hooks/stop.py` (imports): Uses announce() for session-done ping; refactored this session
- `askr/hooks/notification.py` (imports): Uses announce() for quota warnings and permission-prompt alerts; refactored this session
- `askr/state/config.py` (configures): Defines default voice (VOICE_DEFAULT); changed from Samantha to Zarvox this session
- `tests/test_voice.py` (tested_by): Tests voice pipeline; verified passing after refactor
