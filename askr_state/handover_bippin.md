# Handover: bippin

Last updated: 2026-07-10 00:06

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented comprehensive voice-output logging to voice_log.jsonl, capturing every spoken-output attempt with timestamp, exact text, gate-off reason (if applicable), and caller context; fixed brittle test assertions in test_voice.py; and validated all 215 tests passing.

## Discussion
This session added end-to-end voice-output diagnostics by threading caller context (source tag, project_path, session_id) through five call sites in lifecycle.py and stop.py, then logging every speak()/speak_signature()/announce() attempt to ~/.config/askr/voice_log.jsonl regardless of whether the system actually spoke. This captures both successful announcements and gated-off attempts (disabled, non-macOS, missing `say` binary, subprocess failure), making it possible to diagnose repeated or missing announcements by disk lookup instead of code inspection. Two brittle test assertions that checked exact call signatures were refactored to inspect call_args separately, improving test maintainability. All 215 tests pass; changes committed to main.

## Accomplishments
- [x] Implemented voice_log.jsonl logging: every speak()/speak_signature()/announce() call now appends timestamp, exact text, gate-off reason (if any), and caller context (source tag, project_path, session_id)
- [x] Threaded caller context through five call sites: lifecycle.py quota-warning, idle checkpoint, companion-session open, _write_notification; stop.py relaunch-notification and _speak_session_done, each tagged with source string for diagnostic lookup
- [x] Refactored two brittle test assertions in test_voice.py to inspect call_args separately instead of checking exact call signature, improving test robustness
- [x] Added VoiceLoggingTests class with 6 new unit tests covering voice_log.jsonl entry structure, gate-off reasons, and caller context threading
- [x] Validated all 215 tests passing after voice logging implementation

## Next Actions
1. Implement Phase 3.15-S0: hard context budget cap (~15% of window, ≈30k tokens) on today's existing full-dump injection, truncating by priority (rejections > decisions > architecture > failed approaches) when over budget
   *Why: Direct fix for companion-cascade bug; doesn't depend on any other Phase 3.15 stages; works on current dump as-is; will prevent new companion sessions from starting with already-high context*
2. Implement Phase 3.13 S2–S5: persist rejected-decision tracking (rejected_decisions.json) across session boundaries
   *Why: Unblocks Phase 3.15-S4 (rejected-decisions filter); addresses the broader gap that rejected/decided context doesn't persist strongly enough across session boundaries*
3. Implement Phase 3.15 S1–S3, S5–S7 (full smart context injection pipeline) after S0 is live and tested
   *Why: Completes the context-injection overhaul; S1 pulls from files_in_play/relational_files instead of full dump; S3 ranks decisions by relevance; S5 adds failed-approaches semantic matching*
4. Evaluate whether askr should hold a checkpoint/handover while a subagent is outstanding (vs. just staying quiet about it); if yes, implement the hold logic
   *Why: Current fix prevents false "Done." announcements but doesn't block checkpoints; could stall a real quota/context emergency handoff if a subagent hangs — needs explicit decision on risk tolerance*
5. Run an unattended overnight session to validate that quota-trigger, context-trigger, direction-inference, subagent-completion, and voice-logging fixes hold under real load
   *Why: Pre-launch validation; more likely to succeed now that quota-repeat, context-cascade, direction-inference, subagent-announcement, and voice-output-diagnostics are all addressed*

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
- Every voice-output attempt (speak/speak_signature/announce) is logged to voice_log.jsonl with timestamp, exact text, gate-off reason if applicable, and caller context (source tag, project_path, session_id) — Enables diagnostic lookup of repeated or missing announcements without code inspection; captures both successful and gated-off attempts, making it possible to distinguish "didn't speak because disabled" from "didn't speak because code path never fired"
- Caller context is threaded through five specific call sites (lifecycle.py quota-warning, idle checkpoint, companion-session open, _write_notification; stop.py relaunch-notification and _speak_session_done), each tagged with a source string identifying the code path — Allows voice_log.jsonl entries to be traced back to their originating mechanism without re-deriving it from code; makes it possible to correlate repeated announcements with specific triggers

## Files In Play
- `askr/clients/voice.py`
- `askr/session/lifecycle.py`
- `askr/hooks/stop.py`
- `tests/test_voice.py`

## Relational Files
- `askr/session/post_tool_use.py` (imported_by): Handles usage-API refresh that populates quota_reset_at; the quota-trigger fix depends on understanding when reset_at becomes available
- `askr/cli/askr.py` (imported_by): Terminal statusline display; fixed in prior session to use unified 'chat X%' label
- `extension.js` (configures): IDE extension display; already uses 'chat X%' label; terminal now matches
- `tests/test_lifecycle.py` (tested_by): Tests lifecycle trigger logic including quota and context triggers; validates dedup behavior

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Phase 3.13 S2 (rejected_decisions.json persistence) not yet built — blocks Phase 3.15-S4 (rejected-decisions filter)
