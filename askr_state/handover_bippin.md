# Handover: bippin

Last updated: 2026-07-11 18:55

*Source of truth: `handover_bippin.json`*


## Task
Fixed a critical PID-based session liveness check in the companioned_sessions dedup to prevent duplicate companion openings after machine sleep, updated all related tests, and verified 296 passing tests across the full suite.

## Discussion
The companioned_sessions dedup was pruning entries based on stats file staleness (10 minutes without tool calls), but stats files stop updating during machine sleep, not just session termination. After waking from sleep longer than 10 minutes, a live suspended session would appear brand new to the dedup, causing the 60% context companion trigger to fire again for the same session. The fix replaces stats-based pruning with PID-based liveness checks: a suspended process keeps a valid PID indefinitely and only fails the check once genuinely terminated. This is the third distinct bug in the companion-opening flow, separate from the turn-wait timing fix and the self-continuation gate revert.

## Accomplishments
- [x] Implemented PID-based session liveness checking in registry.py to replace stats-file staleness pruning
- [x] Updated lifecycle.py to use registry.is_session_pid_alive() for companioned_sessions dedup pruning
- [x] Created new test_registry.py with 7 passing tests for PID-based liveness logic
- [x] Rewrote PruneCompanionedSessionsTests in test_voice.py to mock registry.is_session_pid_alive instead of stats
- [x] Verified full test suite: 296 tests passing, all pruning tests passing
- [x] Committed and pushed all changes; restarted daemon

## Next Actions
1. Monitor daemon behavior across multiple Mac sleep/wake cycles to confirm PID-based pruning prevents duplicate companion openings
   *Why: This is the third distinct bug in the companion flow; empirical validation across real sleep cycles is critical before considering the issue fully resolved*
2. Review the companion-opening flow end-to-end (trigger → wait logic → dedup → open) to identify any remaining edge cases or timing windows
   *Why: Three separate bugs in this flow suggest the overall design may have other latent issues; a comprehensive audit could prevent future regressions*

## Decisions
- Self-continuation launch gate (a session relaunching itself) should not exist — only Phase 5 teammate-task gate applies — Self-continuation relaunches are the normal case and should never be gated; the original Phase 5 gate already handles the actual threat (unrelated teammate tasks with elevated permissions). The self-continuation gate was overly broad and broke the expected relaunch workflow.
- The 60% context companion trigger is core functionality and must remain; the bug was in timing, not in the trigger's existence — The companion-before-hard-wall feature is the entire point of askr. The bug was that _wait_for_turn_to_finish only waited for one specific turn, allowing new turns to start in the gap between that turn finishing and the companion actually opening. The fix is to also require no turn currently be in flight, not to remove the trigger.
- Companion opening must check both that the watched turn has finished AND that no new turn is currently active before proceeding — The previous logic only checked the first condition, allowing the companion to open right as a new turn started if the user sent a message in the gap. Checking both conditions prevents mid-run interruptions while preserving the 60% context trigger.
- Companioned_sessions dedup pruning must check whether a session's actual process is still alive (PID-based), not whether its stats file has gone stale — Stats files stop updating whenever the machine sleeps, not just when a session ends. A suspended process keeps a valid PID the whole time it's asleep — it only fails that check once it's genuinely gone. PID-based checking prevents the dedup from forgetting live sessions after Mac sleep.

## Failed Approaches
- Allowing test_launch_gate.py and test_permission_gate.py to patch only voice.speak without also patching voice.speak_signature — speak_signature() is the fallback when voice mode is enabled; patching only speak() left real macOS `say` subprocess calls firing and polluting voice_log.jsonl with test fixture entries.
- Gating self-continuation relaunches (a session relaunching itself) with a permission gate — Self-continuation is the normal case and should never be gated. The original Phase 5 gate already handles the actual threat (unrelated teammate tasks with elevated permissions). Gating self-continuation broke the expected relaunch workflow and was unnecessary.
- Assuming the permission gate was responsible for the mid-run companion opening bug — The permission gate revert did not fix the issue. Root cause was a separate timing bug in _wait_for_turn_to_finish: it only waited for the one turn active when the trigger fired, then opened the companion immediately after that turn's Stop event, allowing new turns to start in the gap.
- Pruning companioned_sessions dedup based on whether a session's stats file had gone stale (10 minutes without a tool call) — Stats files stop updating whenever the machine sleeps, not just when a session ends. After waking from sleep longer than 10 minutes, a live session looks brand new to the dedup, causing the context trigger to fire again for the same session. Must use PID-based liveness check instead.

## Files In Play
- `askr/session/registry.py`
- `askr/session/lifecycle.py`
- `tests/test_registry.py`
- `tests/test_voice.py`

## Relational Files
- `askr/session/registry.py` (imported_by): lifecycle.py now calls registry.is_session_pid_alive() for dedup pruning
- `tests/test_registry.py` (tested_by): New test file covering PID-based liveness logic with 7 passing tests
- `tests/test_voice.py` (tested_by): PruneCompanionedSessionsTests rewritten to mock registry.is_session_pid_alive instead of stats
