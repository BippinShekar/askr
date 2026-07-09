# Handover: bippin

Last updated: 2026-07-10 00:18

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented Phase 3.15 (smart, targeted context injection) by building build_context_injection() to replace full-dump state injection with files_in_play/relational_files targeting, decision/failed-approach relevance ranking, token budget capping at ~30k, and graceful degradation when targeting signals are absent; all 236 tests pass.

## Discussion
This session completed Phase 3.15 (S1–S7) by implementing askr/state/reader.py with build_context_injection(), which transforms context injection from full-dump to targeted. When a handover includes files_in_play/relational_files (S1), injection now pulls snapshots for those files (S2), ranks decisions by TF-IDF relevance to task/next_actions (S3), filters rejected decisions by domain matching (S4, degrades gracefully when Phase 3.13 isn't landed yet), includes failed approaches with recency floor (S5), caps total output at ~30k tokens by dropping lower-priority sections rather than truncating mid-sentence (S6), and falls back to full-dump for pre-3.11 handovers with no targeting signal (S7). 21 new tests validate all paths including real project data. Roadmap marked Phase 3.15 complete. All 236 tests pass; changes committed to main.

## Accomplishments
- [x] Implemented build_context_injection() in askr/state/reader.py: replaces full-dump state injection with targeted injection using files_in_play/relational_files when present
- [x] Phase 3.15-S1: Targets RELEVANT FILES section to in-play/relational files instead of all state files
- [x] Phase 3.15-S2: Pulls snapshot purpose text for targeted files when .llm_snapshot exists, degrades to bare paths when absent
- [x] Phase 3.15-S3: Ranks decisions by TF-IDF relevance to handover task/next_actions instead of just most recent 20
- [x] Phase 3.15-S4: Filters rejected decisions by domain matching in-play/relational files, degrades gracefully when Phase 3.13 not yet landed
- [x] Phase 3.15-S5: Wired failed approaches into context injection for first time with relevance ranking and recency floor (last 3)
- [x] Phase 3.15-S6: Implemented token budget cap at ~30k (15% of 200k window), drops whole lower-priority sections (rejections > decisions > architecture > failed approaches) rather than truncating mid-sentence
- [x] Phase 3.15-S7: Graceful fallback to full-dump behavior for pre-3.11 handovers with no targeting signal
- [x] Added 21 new unit tests in tests/test_context_injection.py covering all Phase 3.15 stages, validated against real project handover/decision data
- [x] Updated roadmap.md to mark Phase 3.15 complete with all 7 stages verified against code
- [x] Validated all 236 tests passing after Phase 3.15 implementation

## Next Actions
1. Implement Phase 3.13 S2–S5: persist rejected-decision tracking (rejected_decisions.json) across session boundaries
   *Why: Phase 3.15-S4 now filters rejected decisions by domain but degrades when Phase 3.13 isn't landed; this unblocks full rejected-decisions filtering and addresses the broader gap that rejected/decided context doesn't persist strongly enough across session boundaries*
2. Implement Phase 3.14: .llm_snapshot generation for all source files (purpose text extraction and caching)
   *Why: Phase 3.15-S2 currently degrades to bare paths when .llm_snapshot doesn't exist; Phase 3.14 will populate snapshots so targeted files always have purpose context in injection*
3. Evaluate whether askr should hold a checkpoint/handover while a subagent is outstanding (vs. just staying quiet about it); if yes, implement the hold logic
   *Why: Current fix prevents false "Done." announcements but doesn't block checkpoints; could stall a real quota/context emergency handoff if a subagent hangs — needs explicit decision on risk tolerance*
4. Run an unattended overnight session to validate that quota-trigger, context-trigger, direction-inference, subagent-completion, voice-logging, and Phase 3.15 context-injection fixes hold under real load
   *Why: Pre-launch validation; more likely to succeed now that all prior fixes are in place and Phase 3.15 smart injection is live*

## Decisions
- Gate session launch on dangerous permissions — Companion sessions inherit the exact same zero-friction permission state from their triggering session; without a gate, a dangerous session's autonomous relaunch would bypass approval entirely
- IDE notifications task_approval_pending and guard_warning are rendered as purpose-built popups with context-specific actions rather than generic fallback messages — Generic fallback handling left users with no way to act on these notifications; purpose-built cases provide clear action paths and match the non-blocking design intent
- Terminal statusline and CLI output use unified label 'chat X%' for per-chat context-window percentage, matching IDE extension display — Both surfaces measure the same metric; using identical labels eliminates user confusion and provides consistent terminology across all UI surfaces
- Quota hard-trigger gates on populated quota_reset_at before firing; if reset_at is unknown (fresh per-session stats file), trigger holds off and retries next poll cycle instead of firing blind with no dedup memory — quota_triggered_windows.json dedup is keyed on quota_reset_at; firing without it present means the dedup guard never engages, causing re-announcement on every poll cycle. Mirrors the soft 75% warning which already gates on reset_at.
- Signal 4 (git-log clustering) excludes askr's own automated checkpoint/idle commits via --invert-grep — These commits contribute zero signal (message doesn't match scope regex, files always under askr_state/); during idle-heavy stretches they dilute the real-commit sample from ~10 to as few as 4, tanking confidence from 0.85 to 0.50
- Signal 3 (handover next_actions) skips degraded fallback placeholders (generic "review manually" text) that were being accepted as confident 0.85 directions despite failed handover generation — Fallback text is a sentinel for failed generation, not a real next step; accepting it masks the failure and feeds garbage direction to the next session
- _speak_session_done() stays silent when a dispatched subagent (Agent tool call) is still outstanding, even if a goal looks completed — Subagent output arrives as a separate turn via task-notification; announcing "Done." while it's still running is false and confusing, and the subagent's result could still change the outcome
- companioned_sessions dedup flag is pruned by liveness (removed after session ends) rather than cleared after every Stop turn — Stop fires per-turn, not per-session-end; clearing after every turn meant the flag was always empty by the next poll cycle, allowing context-trigger to re-fire repeatedly on the same companion session
- Every voice-output attempt (speak/speak_signature/announce) is logged to voice_log.jsonl with timestamp, exact text, gate-off reason if applicable, and caller context (source tag, project_path, session_id) — Enables diagnostic lookup of repeated or missing announcements without code inspection; captures both successful and gated-off attempts, making it possible to distinguish "didn't speak because disabled" from "didn't speak because code path never fired"
- Caller context is threaded through five specific call sites (lifecycle.py quota-warning, idle checkpoint, companion-session open, _write_notification; stop.py relaunch-notification and _speak_session_done), each tagged with a source string identifying the code path — Allows voice_log.jsonl entries to be traced back to their originating mechanism without re-deriving it from code; makes it possible to correlate repeated announcements with specific triggers
- Phase 3.15 context injection targets files_in_play/relational_files when present, ranks decisions/failed-approaches by TF-IDF relevance, caps output at ~30k tokens by dropping lower-priority sections, and gracefully degrades to full-dump for pre-3.11 handovers — Targeted injection reduces token waste on irrelevant state, relevance ranking surfaces the most actionable decisions/approaches, token budget prevents context-trigger cascade, and graceful degradation ensures no session breaks on missing targeting signals
- Phase 3.15-S2 (snapshot pulling) degrades to bare file paths when .llm_snapshot doesn't exist, does not block on Phase 3.14 — Phase 3.14 isn't built yet; graceful degradation allows Phase 3.15 to land and provide value immediately while Phase 3.14 can follow independently
- Phase 3.15-S4 (rejected-decisions filtering) degrades to empty when rejected_decisions.json doesn't exist, does not block on Phase 3.13 — Phase 3.13 isn't built yet; graceful degradation allows Phase 3.15 to land and provide value immediately; filtering will automatically populate once Phase 3.13 lands

## Files In Play
- `askr/state/reader.py`
- `tests/test_context_injection.py`
- `roadmap.md`

## Relational Files
- `askr/session/lifecycle.py` (imported_by): Calls build_context_injection() to populate context for session handover; Phase 3.15 injection is consumed here
- `askr/state/writer.py` (imported_by): Writes handover files that Phase 3.15 reads; files_in_play/relational_files targeting depends on these being populated correctly
- `tests/test_lifecycle.py` (tested_by): Tests lifecycle trigger logic; Phase 3.15 context injection affects context-trigger behavior
- `askr_state/decisions.jsonl` (configures): Source data for Phase 3.15-S3 decision relevance ranking; TF-IDF corpus
- `askr_state/failed_approaches.jsonl` (configures): Source data for Phase 3.15-S5 failed-approaches injection; first time this file is read back into context

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Phase 3.13 S2 (rejected_decisions.json persistence) not yet built — Phase 3.15-S4 degrades gracefully but full filtering blocked
- Phase 3.14 (.llm_snapshot generation) not yet built — Phase 3.15-S2 degrades to bare paths but full snapshot pulling blocked
