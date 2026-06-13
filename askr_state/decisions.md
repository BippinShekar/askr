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
[2026-06-13 23:03] [bippin] Focus tweet on solution/outcome, not problem narrative. Reason: User's previous tweets established the pain point; new tweet should show askr as the answer to build credibility and interest
[2026-06-13 23:05] [bippin] Do not post a solution/feature announcement tweet now. Reason: Askr is not publicly launchable yet (~1 week out). Premature announcement risks credibility if launch slips or feature changes.
[2026-06-13 23:05] [bippin] Focus on replies to existing high-reach threads instead of standalone posts. Reason: Replies to @lachygroom, @swyx, @levelsio, @marc_louvion threads will reach the exact audience already interested in this problem. Higher ROI than cold posts.
[2026-06-13 23:11] [bippin] Do not post detailed solution tweet yet; keep positioning vague until 1-week launch window. Reason: askr not ready for public use. Premature reveal kills launch momentum and credibility.
[2026-06-13 23:11] [bippin] Prioritize authentic engagement over direct promotion for reach building. Reason: User has zero time for traditional marketing. Engagement in existing communities is only scalable path.
[2026-06-13 23:14] [bippin] Do not post solution-focused tweets until askr is publicly available. Reason: User explicitly stated askr is one week out and not ready; premature reveals kill launch momentum
[2026-06-13 23:14] [bippin] Lead with pain point (context loss across sessions) rather than product features. Reason: User's proposed angle is stronger and doesn't require revealing askr exists yet
[2026-06-13 23:15] [bippin] Use sarcasm/irony tone ('Damn building with claude makes my life so much easier') rather than earnest problem statement. Reason: User rejected earnest framing as 'gay as hell'; sarcasm lands better with technical audience and positions user as someone who understands the pain deeply
[2026-06-13 23:15] [bippin] Mention three pain points (context loss, machine switching, handoff overhead) rather than two. Reason: Two problems make askr look narrow; three establish a pattern and justify a dedicated tool
[2026-06-13 23:15] [bippin] Do not mention askr by name or reveal it's a product in this tweet. Reason: Product launches in 1 week; tweet is teaser to keep narrative arc alive, not announcement
[2026-06-13 23:16] [bippin] Use sarcasm opener ('building with claude makes your life so much easier') instead of earnest problem statement. Reason: Lands better, signals you understand the irony, avoids sounding weak or whiny
[2026-06-13 23:16] [bippin] Expand from two problems to three (machine switching, co-founder handoff, repeated session setup) to show pattern recognition. Reason: Two problems make askr look narrow; three establish that this is a systemic issue, not edge cases
[2026-06-13 23:16] [bippin] Do not reveal the solution in this tweet; keep it one week out. Reason: User is still building; premature reveal kills momentum and looks unfinished
