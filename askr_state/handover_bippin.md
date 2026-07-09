# Handover: bippin

Last updated: 2026-07-09 23:40

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented a Phase 5 approval gate for autonomous session relaunch, added IDE popup handlers, fixed critical transcript-truncation and race-condition bugs, unified statusline labeling, eliminated repeated quota-trigger announcements, diagnosed and fixed the context-trigger cascade root cause, resolved direction-inference signal quality gaps (Signals 3 and 4), and prevented premature session-completion announcements while dispatched subagents are still outstanding.

## Discussion
This session completed the investigation of direction-inference signal quality (Signal 3 and 4 gaps identified in prior sessions). Signal 4 was sampling askr's own automated checkpoint/idle commits which contribute nothing to direction inference — now excluded via invert-grep. Signal 3 was accepting degraded fallback handover placeholders as confident directions, masking failed handover generation — now skipped via sentinel detection. The session also discovered and fixed a critical subagent completion bug: Stop fires per-turn (not per-session-end), so it was announcing "Done." while dispatched Agent subagents were still running and their results would still feed into the task. _has_outstanding_subagent() now checks the transcript for any Agent tool_use with no matching later task-notification, and _speak_session_done() stays silent when one is outstanding. A third fix addressed the actual root cause of repeated context-trigger announcements: stop.py was clearing the companioned_sessions dedup flag after every turn instead of pruning by liveness. All 209 tests passing; all changes committed to main.

## Accomplishments
- [x] Fixed Signal 4 (git-log clustering) dilution: excluded askr's own automated checkpoint/idle commits via --invert-grep, preventing low-signal commits from reducing confidence
- [x] Fixed Signal 3 (handover next_actions) masking: skip degraded fallback placeholders (generic "review manually") that were accepted as confident 0.85 directions despite failed handover generation
- [x] Fixed premature session-completion announcements: _speak_session_done() now detects outstanding dispatched subagents (Agent tool calls with no matching task-notification) and stays silent until they report back
- [x] Fixed repeated context-trigger announcements root cause: stop.py was clearing companioned_sessions dedup flag after every turn; now prunes by liveness instead
- [x] Added 10 new unit tests covering Signal 3/4 quality fixes and subagent completion detection against real temp git repos

## Next Actions
1. Implement Phase 3.15-S0: hard context budget cap (~15% of window, ≈30k tokens) on today's existing full-dump injection, truncating by priority (rejections > decisions > architecture > failed approaches) when over budget
   *Why: Direct fix for companion-cascade bug; doesn't depend on any other Phase 3.15 stages; works on current dump as-is; will prevent new companion sessions from starting with already-high context*
2. Implement Phase 3.13 S2–S5: persist rejected-decision tracking (rejected_decisions.json) across session boundaries
   *Why: Unblocks Phase 3.15-S4 (rejected-decisions filter); addresses the broader gap that rejected/decided context doesn't persist strongly enough across session boundaries*
3. Implement Phase 3.15 S1–S3, S5–S7 (full smart context injection pipeline) after S0 is live and tested
   *Why: Completes the context-injection overhaul; S1 pulls from files_in_play/relational_files instead of full dump; S3 ranks decisions by relevance; S5 adds failed-approaches semantic matching*
4. Evaluate whether askr should hold a checkpoint/handover while a subagent is outstanding (vs. just staying quiet about it); if yes, implement the hold logic
   *Why: Current fix prevents false "Done." announcements but doesn't block checkpoints; could stall a real quota/context emergency handoff if a subagent hangs — needs explicit decision on risk tolerance*
5. Run an unattended overnight session to validate that quota-trigger, context-trigger, direction-inference, and subagent-completion fixes hold under real load
   *Why: Pre-launch validation; more likely to succeed now that quota-repeat, context-cascade, direction-inference, and subagent-announcement issues are all addressed*

## Decisions
- Gate session launch on dangerous permissions — Companion sessions inherit the exact same zero-friction permission state from their triggering session; without a gate, a dangerous session's autonomous relaunch would bypass approval entirely
- IDE notifications task_approval_pending and guard_warning are rendered as purpose-built popups with context-specific actions rather than generic fallback messages — Generic fallback handling left users with no way to act on these notifications; purpose-built cases provide clear action paths and match the non-blocking design intent
- Terminal statusline and CLI output use unified label 'chat X%' for per-chat context-window percentage, matching IDE extension display — Both surfaces measure the same metric; using identical labels eliminates user confusion and provides consistent terminology across all UI surfaces
- Quota hard-trigger gates on populated quota_reset_at before firing; if reset_at is unknown (fresh per-session stats file), trigger holds off and retries next poll cycle instead of firing blind with no dedup memory — quota_triggered_windows.json dedup is keyed on quota_reset_at; firing without it present means the dedup guard never engages, causing re-announcement on every poll cycle. Mirrors the soft 75% warning which already gates on reset_at.
- Phase 3.15-S0 (hard context budget cap) is the immediate priority for fixing context-trigger cascade, not the full S1–S7 pipeline — S0 is a minimal, isolated fix that works on today's full-dump injection without depending on S1–S7; it directly prevents new companions from starting with already-high context; S1–S7 can follow after S0 is validated
- Signal 4 (git-log clustering) excludes askr's own automated checkpoint/idle commits via --invert-grep — These commits contribute zero signal (message doesn't match scope regex, files always under askr_state/); during idle-heavy stretches they dilute the real-commit sample from ~10 to as few as 4, tanking confidence from 0.85 to 0.50
- Signal 3 (handover next_actions) skips degraded fallback placeholders (generic "review manually" text) that were being accepted as confident 0.85 directions despite failed handover generation — Fallback text is a sentinel for failed generation, not a real next step; accepting it masks the failure and feeds garbage direction to the next session
- _speak_session_done() stays silent when a dispatched subagent (Agent tool call) is still outstanding, even if a goal looks completed — Subagent output arrives as a separate turn via task-notification; announcing "Done." while it's still running is false and confusing, and the subagent's result could still change the outcome
- companioned_sessions dedup flag is pruned by liveness (removed after session ends) rather than cleared after every Stop turn — Stop fires per-turn, not per-session-end; clearing after every turn meant the flag was always empty by the next poll cycle, allowing context-trigger to re-fire repeatedly on the same companion session

## Files In Play
- `askr/hooks/stop.py`
- `askr/session/lifecycle.py`
- `tests/test_voice.py`
- `tests/test_infer_direction_signal_quality.py`

## Relational Files
- `askr/session/post_tool_use.py` (imported_by): Handles usage-API refresh that populates quota_reset_at; the quota-trigger fix depends on understanding when reset_at becomes available
- `askr/cli/askr.py` (imported_by): Terminal statusline display; fixed in prior session to use unified 'chat X%' label
- `extension.js` (configures): IDE extension display; already uses 'chat X%' label; terminal now matches
- `tests/test_lifecycle.py` (tested_by): Tests lifecycle trigger logic including quota and context triggers; validates dedup behavior

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Phase 3.13 S2 (rejected_decisions.json persistence) not yet built — blocks Phase 3.15-S4 (rejected-decisions filter)
