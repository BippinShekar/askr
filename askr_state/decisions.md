# Decisions

Append-only. One line per decision. Never edit existing lines.

Format: [YYYY-MM-DD HH:MM] [developer] Decision text. Reason: reason text.

[2026-06-13 21:33] [bippin] Chose to handle both dict and str goal formats in checkpoint.py rather than enforcing a single type. Reason: Provides backward compatibility with existing checkpoints while supporting new JSON-serialized format
[2026-06-13 21:33] [bippin] Implemented delta extraction at the hook level (post_tool_use.py) rather than in checkpoint.py. Reason: Separates concerns: hooks capture raw deltas, checkpoint orchestrates persistence
[2026-06-13 21:54] [bippin] Focus on hook payload inspection rather than binary reverse-engineering of compaction algorithm. Reason: Hook payloads are more directly actionable for improving handover; binary strings provide limited actionable insight
[2026-06-13 22:06] [bippin] Did not refactor _turns_remaining() signature or add new parameters; fixed calculation in-place. Reason: Minimal change surface area reduces risk of introducing new bugs; cost_summary already provides all needed data
[2026-06-13 22:06] [bippin] Did not add new cost_summary fields; reused existing context_window. Reason: Field already present and accessible to session_card via cost_summary dict
[2026-06-13 22:14] [bippin] Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers rather than relying on git diffs alone. Reason: Investigation revealed these files control autonomous session continuation; git state alone is insufficient for proper handover
[2026-06-13 22:14] [bippin] Prioritize staging verification of checkpoint card display before pushing report_image.py fixes. Reason: Verification must confirm the fix works in practice before committing to main branch
[2026-06-13 22:24] [bippin] Handover system requires architectural redesign, not incremental fix.. Reason: User characterized current behavior as 'catastrophic failure'—stale checkpoints are a fundamental timing issue, not a data formatting problem.
[2026-06-13 22:24] [bippin] Goal inference must be deferred until session-end validation, not auto-inferred mid-session.. Reason: User reported auto-inferred goals becoming stale and out of sync with actual session progress—inference timing is the root cause.
[2026-06-13 22:32] [bippin] Root cause is NOT a race condition or async timing issue — it is a logic gap where stop checkpoint handler is never invoked. Reason: User correctly identified that handover creation happens after all session actions, so if it's stale, the creation itself failed
[2026-06-13 22:32] [bippin] Goal inference must be session-aware, not message-aware. Reason: Auto-inferring goals from old user messages creates stale objectives that poison autonomous handovers
[2026-06-13 22:57] [bippin] Auto-suggested goals are tagged at inference time (session_start.py) rather than at goal creation time. Reason: Allows distinction between user-created goals and system-inferred goals; enables selective expiry without affecting user intent
[2026-06-13 22:57] [bippin] Expiry happens at checkpoint end, after completed goals are processed, not at session start. Reason: Ensures completed auto-suggested goals are recorded in checkpoint before removal; prevents loss of completion signal
[2026-06-13 22:57] [bippin] Timestamp gate uses 5-minute staleness threshold on checkpoint_pending.json. Reason: Balances avoiding stale checkpoints while allowing legitimate multi-session workflows with brief pauses
[2026-06-13 22:58] [bippin] Cost notifications will be sent to Discord instead of displayed in terminal. Reason: User explicitly stated this preference; cleaner UX and persistent record in Discord
[2026-06-13 22:58] [bippin] Cost tracking will be unified across both `cmd_init()` and `.llm_snapshot` generation. Reason: Both use Claude API; single aggregation point reduces duplication and ensures no calls are missed
