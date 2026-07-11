# Handover: bippin

Last updated: 2026-07-11 11:37

*Source of truth: `handover_bippin.json`*


## Task
Fixed a critical launch gate bug that silently blocked every relaunch on every project by narrowing session liveness checks to the current session only, added voice announcements for held relaunches, and verified the fix across 295 passing tests.

## Discussion
The launch gate introduced yesterday was treating broadly-pre-approved Bash (which Phase 3.8 deliberately builds up on any actively-used project) identically to --dangerously-skip-permissions, causing it to fire on every project. Additionally, the function holding a relaunch had no voice line, making held relaunches completely invisible. This session root-caused both bugs via voice_log.jsonl analysis, fixed the permission gate to check only the current session's liveness (not any session in the directory), added proper voice alerts for held relaunches, and confirmed the fix with 295 passing tests and live daemon restart.

## Accomplishments
- [x] Fixed permission_gate.py to check only current session liveness instead of any session existence in project directory
- [x] Added voice announcement in lifecycle._notify_launch_held() for held relaunches
- [x] Removed test suite pollution by patching voice.speak and voice.speak_signature in test_launch_gate.py and test_permission_gate.py
- [x] Verified fix with full test suite: 295 passed in 6.6s, voice_log.jsonl clean
- [x] Committed fix (61a3c61) and restarted daemon to pick up changes live

## Next Actions
1. Monitor leaps project relaunch behavior — it has genuine --dangerously-skip-permissions set, so it should now correctly hold and announce via voice instead of silently blocking
   *Why: Confirms the fix distinguishes between false-positive broad Bash and real dangerous permissions flags*
2. Run `askr launch approve` from leaps project if you want to unblock the held relaunch manually
   *Why: The gate is working as designed; approval is the intended user action for dangerous permission flags*

## Decisions
- Launch gate permission check must verify only the CURRENT session is still running, not whether ANY session exists in the project — Old sessions remain in the project directory after they end; checking for any session caused every relaunch attempt to be silently blocked. Narrowing to current session allows relaunches while still preventing concurrent runs of the same session.
- Held relaunches must have a voice announcement via lifecycle._notify_launch_held() — Without voice output, held relaunches were completely invisible to the user; voice_log.jsonl showed zero trigger-related output across 25+ hours. Voice announcement makes the gate's action observable.

## Failed Approaches
- Checking for any session in project directory to gate relaunches in permission_gate.py — Old sessions remain in the project directory after they end; checking for any session blocks every relaunch attempt. Must check only the current session's liveness.
- Allowing test_launch_gate.py and test_permission_gate.py to patch only voice.speak without also patching voice.speak_signature — speak_signature() is the fallback when voice mode is enabled; patching only speak() left real macOS `say` subprocess calls firing and polluting voice_log.jsonl with test fixture entries.

## Files In Play
- `askr/session/permission_gate.py`
- `askr/session/lifecycle.py`
- `tests/test_launch_gate.py`
- `tests/test_permission_gate.py`

## Relational Files
- `askr/clients/voice.py` (imported_by): lifecycle._notify_launch_held() calls voice.announce(); test patches target voice.speak and voice.speak_signature
- `~/.config/askr/voice_log.jsonl` (configures): Machine-wide voice output log used to diagnose the silent-blocking bug; latest entry confirms fix is working
- `askr_state/failed_approaches.md` (configures): Appended new failed approach entry documenting the session liveness check bug
