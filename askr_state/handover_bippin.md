# Handover: bippin

Last updated: 2026-07-11 14:50

*Source of truth: `handover_bippin.json`*


## Task
Fixed a critical launch gate bug that silently blocked every relaunch on every project, added voice announcements for held relaunches, verified the fix across 295 passing tests, reverted the self-continuation launch gate entirely after determining it was overly broad and unnecessary, then identified and fixed a separate timing bug in the 60% context companion trigger that could open mid-run if a new turn started in the gap between the watched turn finishing and the companion actually opening.

## Discussion
The launch gate introduced yesterday was treating broadly-pre-approved Bash identically to --dangerously-skip-permissions, causing it to fire on every project. This was root-caused via voice_log.jsonl analysis, fixed by checking only the current session's liveness, and verified with 295 passing tests. The self-continuation gate was then reverted entirely as overly broad and unnecessary — the original Phase 5 permission gate only applies to teammates' queued tasks with elevated permissions. However, a separate bug existed in `_wait_for_turn_to_finish`: it only waited for the one turn active when the 60% context trigger fired, then opened the companion the instant that turn's Stop event landed. If a new message arrived in that gap (normal in active back-and-forth), the companion would pop up right as the next turn started, appearing to interrupt. This session fixed the timing logic to also require no turn currently be in flight before acting, added 5 new tests, verified 288 total passing, and restarted the daemon live.

## Accomplishments
- [x] Fixed permission_gate.py to check only current session liveness instead of any session existence in project directory
- [x] Added voice announcement in lifecycle._notify_launch_held() for held relaunches
- [x] Removed test suite pollution by patching voice.speak and voice.speak_signature in test_launch_gate.py and test_permission_gate.py
- [x] Verified fix with full test suite: 295 passed in 6.6s, voice_log.jsonl clean
- [x] Committed fix (61a3c61) and restarted daemon to pick up changes live
- [x] Reverted self-continuation launch gate entirely from lifecycle.py, permission_gate.py, askr.py, and vscode-extension/extension.js
- [x] Removed dead dangerous_autolaunch_pending case from IDE extension
- [x] Updated roadmap.md to reflect removal of self-continuation gate and clarify Phase 5 teammate-task gate remains
- [x] Verified revert with full test suite: 283 passed in 2.9s
- [x] Committed revert (79ebf94) and restarted daemon live
- [x] Identified timing bug in _wait_for_turn_to_finish: it only waited for the one turn active when trigger fired, then opened companion immediately after that turn's Stop event, allowing new turns to start in the gap
- [x] Fixed _wait_for_turn_to_finish to also check that no turn is currently active before opening companion, preventing mid-run interruptions
- [x] Created test_turn_wait.py with 5 new tests covering the timing fix
- [x] Verified timing fix with full test suite: 288 passed
- [x] Committed timing fix (b7951a7) and restarted daemon live

## Next Actions
1. Monitor companion opening behavior during active back-and-forth sessions — companion should open at 60% context only when no turn is currently in flight, never interrupting mid-run
   *Why: Confirms the timing fix prevents the mid-run opening bug while preserving the core 60% context trigger functionality*
2. Verify self-continuation relaunches proceed without any permission gate, matching pre-yesterday behavior
   *Why: Confirms the self-continuation gate revert is working correctly*
3. Verify Phase 5 teammate-task permission gate still fires correctly when a teammate's queued task runs in a session with elevated permissions
   *Why: The only permission gate that should remain active is the original Phase 5 one for unrelated tasks; confirm it still works as designed*

## Decisions
- Launch gate permission check must verify only the CURRENT session is still running, not whether ANY session exists in the project — Old sessions remain in the project directory after they end; checking for any session caused every relaunch attempt to be silently blocked. Narrowing to current session allows relaunches while still preventing concurrent runs of the same session.
- Held relaunches must have a voice announcement via lifecycle._notify_launch_held() — Without voice output, held relaunches were completely invisible to the user; voice_log.jsonl showed zero trigger-related output across 25+ hours. Voice announcement makes the gate's action observable.
- Self-continuation launch gate (a session relaunching itself) should not exist — only Phase 5 teammate-task gate applies — Self-continuation relaunches are the normal case and should never be gated; the original Phase 5 gate already handles the actual threat (unrelated teammate tasks with elevated permissions). The self-continuation gate was overly broad and broke the expected relaunch workflow.
- The 60% context companion trigger is core functionality and must remain; the bug was in timing, not in the trigger's existence — The companion-before-hard-wall feature is the entire point of askr. The bug was that _wait_for_turn_to_finish only waited for one specific turn, allowing new turns to start in the gap between that turn finishing and the companion actually opening. The fix is to also require no turn currently be in flight, not to remove the trigger.
- Companion opening must check both that the watched turn has finished AND that no new turn is currently active before proceeding — The previous logic only checked the first condition, allowing the companion to open right as a new turn started if the user sent a message in the gap. Checking both conditions prevents mid-run interruptions while preserving the 60% context trigger.

## Failed Approaches
- Checking for any session in project directory to gate relaunches in permission_gate.py — Old sessions remain in the project directory after they end; checking for any session blocks every relaunch attempt. Must check only the current session's liveness.
- Allowing test_launch_gate.py and test_permission_gate.py to patch only voice.speak without also patching voice.speak_signature — speak_signature() is the fallback when voice mode is enabled; patching only speak() left real macOS `say` subprocess calls firing and polluting voice_log.jsonl with test fixture entries.
- Gating self-continuation relaunches (a session relaunching itself) with a permission gate — Self-continuation is the normal case and should never be gated. The original Phase 5 gate already handles the actual threat (unrelated teammate tasks with elevated permissions). Gating self-continuation broke the expected relaunch workflow and was unnecessary.
- Assuming the permission gate was responsible for the mid-run companion opening bug — The permission gate revert did not fix the issue. Root cause was a separate timing bug in _wait_for_turn_to_finish: it only waited for the one turn active when the trigger fired, then opened the companion immediately after that turn's Stop event, allowing new turns to start in the gap.

## Files In Play
- `askr/session/lifecycle.py`
- `askr/session/permission_gate.py`
- `askr/cli/askr.py`
- `askr/ide/vscode-extension/extension.js`
- `roadmap.md`
- `tests/test_permission_gate.py`
- `tests/test_turn_wait.py`

## Relational Files
- `askr/clients/voice.py` (imported_by): lifecycle._notify_launch_held() calls voice.announce(); test patches target voice.speak and voice.speak_signature
- `~/.config/askr/voice_log.jsonl` (configures): Machine-wide voice output log used to diagnose the silent-blocking bug; latest entry confirms fix is working

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
