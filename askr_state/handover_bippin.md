# Handover: bippin

Last updated: 2026-10-25 14:30

*Source of truth: `handover_bippin.json`*


## Task
Instrumented PreCompact emergency kills and native-resume watch with session-level diagnostics, added ASKR_DEVELOPER environment override for multi-user bot scenarios, and marked superseded decisions in audit trail to prevent stale guidance.

## Discussion
Two parallel sessions converged on diagnostic instrumentation to enable root-cause analysis of premature session termination and slow recovery without guessing. Session 1 built the five-stage quota-reset automation pipeline and fixed daemon-suspension gaps during macOS sleep/wake. This session completed Stages 1 and 3 of instrumentation (PreCompact kills now log session_id, context_pct, and already_companioned flag; _watch_for_native_resume logs session_id, resolved reset_at, and grace-adjusted deadline). All 702 tests pass. Additionally, added ASKR_DEVELOPER environment variable override to support shared bots running Claude Code on behalf of multiple users without touching machine-level config, and established a convention for marking reversed decisions with '[SUPERSEDED]' prefix to keep audit trail intact while preventing stale guidance from being read as current.

## Accomplishments
- [x] Instrumented PreCompact emergency SIGKILL with session_id, context_pct at kill time, and already_companioned flag logged AFTER the kill to preserve race-winning behavior
- [x] Instrumented _watch_for_native_resume with session_id, resolved reset_at, and grace-adjusted deadline up front before waiting
- [x] Instrumented quota-fallback log lines in _verify_native_resume_or_cont with session_id, resolved reset_at, and grace-adjusted deadline
- [x] Verified all 702 tests pass after instrumentation changes
- [x] Committed and pushed instrumentation stages (commit 1022c58)
- [x] Implemented independent quota polling in lifecycle.py that fires the trigger even when stats files are stale (root cause of 90% trigger never firing)
- [x] Built five-stage same-session rate-limit auto-resume: detect via live poll → send Escape → target terminal via ancestor-PID → wait for reset with safety net → auto-send 'cont'
- [x] Redesigned guard escape-hatch from auto-allow-after-2-blocks to held-for-approval requiring explicit `askr guard approve/discard`
- [x] Converted all one-shot notification-button handlers (Keep/Discard, Approve/Discard, Add to Goals) to run silently via runAskrSilently() instead of creating visible terminals
- [x] Added `askr graph` CLI command rendering session-spawn tree from events.jsonl with trigger summaries
- [x] Added `askr guard list/approve/discard` CLI commands for managing guard blocks
- [x] Fixed handover hallucination by filtering files_in_play and relational_files against real filesystem before writing
- [x] Implemented next_actions staleness prevention via corpus-overlap matching (65% token threshold) and git-commit cross-checks
- [x] Extended mid-session CLAUDE.md reminder mechanism to combat context-decay adherence drift
- [x] Fixed test suite deadlock in test_turn_wait.py that was silently hanging entire pytest run
- [x] Added test isolation via conftest.py autouse fixture for hook_capture diagnostic logging
- [x] Identified critical daemon-suspension gap during macOS sleep/wake: 1.5-hour gap in daemon.log (18:52–20:36) with zero quota-polling events, blocking overnight autonomous runs
- [x] Fixed daemon-suspension root cause by preventing caffeinate release while quota-wait threads are in flight, using _quota_wait_depth counter to track concurrent quota-wait/premature-activity-watch threads across projects
- [x] Wrapped _execute_quota_trigger with _quota_wait_begin/_quota_wait_end to hold caffeinate alive across session-idle transitions during quota-reset wait, closing the incident where daemon froze for 1h43m mid-wait
- [x] Added ASKR_DEVELOPER environment variable override in load_developer() to support shared bots running Claude Code on behalf of multiple users without modifying machine-level config
- [x] Established convention for marking reversed/retired decisions with '[SUPERSEDED]' prefix in decisions.jsonl to preserve audit trail while preventing stale guidance from being read as current
- [x] Marked '[SUPERSEDED]' on Escape/cont automation decision after this week's work explicitly retired same-session automation because Claude Code now handles quota-resume natively

## Next Actions
1. Monitor daemon.log for next PreCompact kill to confirm Stage 1 diagnostics are working and determine whether Trigger A is losing the race (already_companioned=False) or opening companion but still losing (already_companioned=True)
   *Why: Can't fix the kill complaint without knowing which race is being lost; the log will tell us directly next time it happens*
2. Monitor daemon.log for next slow cont recovery to confirm Stage 3 diagnostics show whether askr was legitimately waiting for a future reset_at or actually stalled mid-wait
   *Why: Can't fix the slow-cont complaint without knowing whether it's a real wait or a stall; the log will show the resolved reset_at and grace-adjusted deadline up front*
3. Clarify what specific factual error or hallucination in handover output to target for Stage 5 — current leaps handover (2026-09-18 14:32) appears factually sound but has poor structure (Task line is run-on, Next Actions mixes urgency levels without markers)
   *Why: Stage 5 is blocked on understanding the concrete quality problem; the current handover is not obviously broken, so need clarification on which handover or what specific error to fix*
4. Commit and push ASKR_DEVELOPER environment override and test_developer_override.py to enable multi-user bot deployments
   *Why: Feature is complete and tested; unblocks shared-bot scenarios where a single daemon serves multiple users*

## Decisions
- Separate the account-wide announcement dedup (quota_triggered_windows, keyed by reset_at) from per-session resume verification (quota_resume_verified, keyed by session_id::reset_at) — Quota is account-wide so the announcement fires once per window by design (correct, stops duplicate voice/Discord spam across concurrent sessions) — but each concurrent session is a separate terminal needing its own resume check. Reusing the same dedup for both silently left every session but the first with nobody watching it after the announcement fired once.
- Maintain 180-second grace buffer after real quota-reset time before checking whether the transcript resumed natively — Allows time for Claude Code to detect the reset, reconnect, and resume writing; 180s is conservative enough to catch slow reconnects without waiting indefinitely; this is intentional design, not a bug
- Accept stale quota percentage (e.g. '99%') in voice announcements when reset has already passed before the announcement fires — Cosmetic wording issue only; the mechanism is correct (Phase 4 verification checks whether transcript actually resumed, not the announced percentage); fixing the wording is lower priority than fixing the concurrent-session verification bug
- Resolve the target pid's tty before emergency SIGKILL and write the mouse-tracking disable sequence (\x1b[?1000l) directly to the device afterward — SIGKILL gives Claude Code's TUI no chance to disable mouse-tracking mode it enables on start, leaving the terminal dumping raw SGR mouse reports as garbage text; direct device write bypasses the killed process entirely
- [SUPERSEDED] Use Escape key (\x1b) for quota-reset menu automation, not arrow-navigation or digit-selection — This week's work explicitly retired same-session Escape/cont automation because Claude Code now handles quota-resume natively; decision is still in audit trail but no longer active guidance
- Implement quota-reset automation in five stages: (1) instrumentation for detection, (2) PID→terminal bridge, (3) wait for real data, (4) wire automation, (5) safety-net detection — Stages 1, 2, and 5 are buildable today without live events and carry no automation risk; Stage 3 requires real quota-limit data; Stage 4 (the only risky stage) waits for Stage 3 before proceeding
- PID→vscode.Terminal targeting uses _get_ancestor_pids to walk the process tree and findTerminalByAncestorPids to match Terminal by ancestor PID — Claude Code may spawn multiple terminal instances; ancestor-PID matching is more reliable than terminal title or index-based targeting and survives terminal renames
- Instrument PreCompact kills with session_id, context_pct, and already_companioned flag logged AFTER the kill to preserve race-winning behavior — Logging before kill would add latency and risk losing the race; logging after preserves the hook's whole point while enabling diagnosis of which race (Trigger A never ran vs. opened companion but lost) is being lost
- Instrument _watch_for_native_resume and quota-fallback paths with session_id, resolved reset_at, and grace-adjusted deadline up front before waiting — Next slow cont can be diagnosed from the log directly instead of reconstructing guesses across multiple incidents; shows whether askr was legitimately waiting for a future reset or actually stalled
- Mark reversed/retired decisions with '[SUPERSEDED]' prefix instead of deleting them or presenting them unmarked as current — Audit trail must stay intact for traceability, but unmarked reversed decisions sitting next to new ones read as stale/naive guidance. Prefix makes the reversal explicit without losing history.
- Support ASKR_DEVELOPER environment variable override in load_developer() for multi-user bot deployments — Shared bots running Claude Code on behalf of many users need per-run identity without touching machine-level config; environment override is the standard pattern for this use case

## Files In Play
- `askr/hooks/pre_compact.py`
- `askr/session/lifecycle.py`
- `askr/state/config.py`
- `tests/test_pre_compact.py`
- `tests/test_developer_override.py`

## Relational Files
- `askr/session/lifecycle.py` (imports): pre_compact.py calls _log() and _latest_stats() from lifecycle.py for diagnostics
- `tests/test_pre_compact.py` (tested_by): 32 tests verify PreCompact kill instrumentation and edge cases
- `tests/test_developer_override.py` (tested_by): Tests ASKR_DEVELOPER environment override behavior in load_developer()
- `askr_state/decisions.jsonl` (configures): Tracks all architectural decisions including the new instrumentation choices and superseded decisions
- `askr_state/events.jsonl` (configures): Records companion-spawn events that correlate with PreCompact kill diagnostics

## Uncommitted Files
- `askr/state/config.py`
- `askr_state/decisions.jsonl`
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`
- `tests/test_developer_override.py`

## Blockers
- Stage 5 (handover quality) blocked on clarification of what specific factual error or hallucination to target — current leaps handover appears factually sound but has poor structure
