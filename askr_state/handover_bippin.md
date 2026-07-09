# Handover: bippin

Last updated: 2026-07-10 00:34

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented Phase 3.13 (persisted user-rejection tracking) and Phase 3.15 (smart, targeted context injection), enabling rejected decisions to persist across sessions and context to be injected selectively by relevance and file targeting; all 289 tests pass.

## Discussion
This session received a task-notification that Phase 3.13 S2–S5 (user-rejection tracking) had completed in a subagent. The subagent built rejection persistence via _write_rejections_from_handover() (S2), guard filtering by domain (S3), real-time regex detection in post_tool_use (S4), and CLAUDE.md guard directive updates (S5), with 4 new test files covering all paths. The subagent's commits merged cleanly onto the concurrent Phase 3.15 work (zero file overlap), and the full suite now passes 289 tests. This session verified the merge, ran the complete test suite in the main worktree, and cleaned up the subagent's isolated git worktree. Both Phase 3.13 and Phase 3.15 are now shipped and integrated.

## Accomplishments
- [x] Verified Phase 3.13 S2–S5 subagent work merged cleanly to main with zero file conflicts against Phase 3.15
- [x] Ran full test suite (289 passing) in main worktree to confirm Phase 3.13 + Phase 3.15 integration
- [x] Cleaned up subagent's isolated git worktree after merge verification
- [x] Confirmed CLAUDE.md guard directive and askr/cli/askr.py template are byte-for-byte synchronized (Phase 3.13 S5)
- [x] Verified rejected_decisions.jsonl wiring end-to-end across checkpoint.py, guard.py, and post_tool_use.py

## Next Actions
1. Decide: should askr hold/block checkpoints while a dispatched subagent (Agent tool call) is outstanding, or just flag it in the handover and let the next session see it?
   *Why: Current fix prevents false "Done." announcements but doesn't block checkpoints; could stall a real quota/context emergency handoff if a subagent hangs — needs explicit decision on risk tolerance before implementing the hold logic*
2. Implement Phase 3.9: Behavioral Preference Persistence (user-preference tracking and recall across sessions)
   *Why: Phase 3.13 file-overlap blocker is now resolved; Phase 3.9 is the next high-value phase on the roadmap and unblocked*
3. Implement Phase 3.14: .llm_snapshot generation for all source files (purpose text extraction and caching)
   *Why: Phase 3.15-S2 currently degrades to bare paths when .llm_snapshot doesn't exist; Phase 3.14 will populate snapshots so targeted files always have purpose context in injection*
4. Run an unattended overnight session to validate that quota-trigger, context-trigger, direction-inference, subagent-completion, voice-logging, Phase 3.13 rejection-tracking, and Phase 3.15 context-injection fixes hold under real load
   *Why: Pre-launch validation; more likely to succeed now that all prior fixes are in place and both Phase 3.13 and Phase 3.15 are live*

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
- Phase 3.13 S2–S5 (user-rejection tracking) persists rejected decisions to rejected_decisions.jsonl with append-only writes, file locking, and substring dedup on what_was_proposed — Mirrors the established pattern from decisions.jsonl and failed_approaches.jsonl; append-only + locking prevents concurrent-write corruption; substring dedup prevents duplicate entries while allowing confidence updates
- Phase 3.13 S3 (guard filtering) matches rejected decisions by simple substring between domain and file being written (either direction), no regex or fuzzy matching — Simple substring match is fast, predictable, and sufficient for the domain-level filtering use case; avoids false positives from overly broad regex patterns
- Phase 3.13 S4 (real-time regex detection) uses regex-only detection with no LLM call, reads only transcript tail (last 64KB), and writes with fixed 0.75 confidence — Regex-only keeps cost near zero on every tool call; transcript tail limits I/O; fixed confidence avoids LLM latency while still allowing manual override via checkpoint writes
- Phase 3.13 S5 (CLAUDE.md guard directive) is kept byte-for-byte synchronized with askr/cli/askr.py template so future askr init runs report "unchanged" — Prevents accidental divergence between the documented guard behavior and the actual template; idempotent init runs are a quality signal

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
