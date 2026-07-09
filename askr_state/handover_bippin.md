# Handover: bippin

Last updated: 2026-07-09 19:46

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented a Phase 5 approval gate for autonomous session relaunch (quota-trigger, context-trigger, goal-autolaunch) that holds dangerous sessions pending explicit approval, added IDE popup handlers for task_approval_pending and guard_warning notifications, fixed critical transcript-truncation bugs, race conditions in lifecycle triggers, false-positive idle-trigger fires, phantom-session warnings, cross-process voice serialization, unified terminal/IDE statusline labeling for context-window percentage display, and eliminated repeated quota-trigger announcements by gating the hard trigger on populated quota_reset_at.

## Discussion
This session diagnosed and fixed the root cause of repeated "quota at X%" voice announcements: quota_triggered_windows.json (the dedup memory keyed on quota_reset_at) remained empty when reset_at was unpopulated from a fresh per-session stats file, allowing the hard trigger to re-fire on every poll cycle. The session also diagnosed the context-trigger cascade (repeated "context past X%" announcements spawning new companion sessions) as a consequence of Phase 3.15 smart context injection not yet being shipped — the current full-dump injection starts new companions with already-high context, crossing the 60% threshold repeatedly with fresh dedup slates. A third issue was identified: talk-only research sessions fall back to weak git-log clustering (0.50 confidence) when no strong signals fire, leaving next_actions unpopulated for the next session. The quota-trigger fix (commit 13de575) is now live; Phase 3.15-S0 (hard context budget cap) is the direct fix for the cascade bug and is the top priority for the next session.

## Accomplishments
- [x] Fixed repeated quota-trigger announcements by gating hard trigger on populated quota_reset_at
- [x] Diagnosed root cause of context-trigger cascade (Phase 3.15 smart injection not yet shipped)
- [x] Diagnosed direction-inference quality gap for talk-only research sessions (Signal 3 weak signal fallback)
- [x] Unified terminal/CLI statusline label to 'chat X%' matching IDE extension

## Next Actions
1. Implement Phase 3.15-S0: hard context budget cap (~15% of window, ≈30k tokens) on today's existing full-dump injection, truncating by priority (rejections > decisions > architecture > failed approaches) when over budget
   *Why: Direct fix for tonight's companion-cascade bug; doesn't depend on any other Phase 3.15 stages; works on current dump as-is; will prevent new companion sessions from starting with already-high context*
2. Investigate why Signal 3 (handover_next_actions) isn't reliably catching talk-only research sessions, causing 0.50 confidence fallback to weak git-log clustering
   *Why: Research-only sessions lose concrete next_actions for the following session; needs audit of recent handover JSON next_actions quality and Stop-hook signal firing conditions*
3. Implement Phase 3.13 S2–S5: persist rejected-decision tracking (rejected_decisions.json) across session boundaries
   *Why: Unblocks Phase 3.15-S4 (rejected-decisions filter); addresses the broader gap that rejected/decided context doesn't persist strongly enough across session boundaries*
4. Implement Phase 3.15 S1–S3, S5–S7 (full smart context injection pipeline) after S0 is live and tested
   *Why: Completes the context-injection overhaul; S1 pulls from files_in_play/relational_files instead of full dump; S3 ranks decisions by relevance; S5 adds failed-approaches semantic matching*
5. Run an unattended overnight session to validate that quota-trigger, context-trigger, and direction-inference fixes hold under real load
   *Why: Pre-launch validation; more likely to succeed now that quota-repeat, context-cascade, and direction-inference issues are addressed*

## Decisions
- Gate session launch on dangerous permissions — Companion sessions inherit the exact same zero-friction permission state from their triggering session; without a gate, a dangerous session's autonomous relaunch would bypass approval entirely
- IDE notifications task_approval_pending and guard_warning are rendered as purpose-built popups with context-specific actions rather than generic fallback messages — Generic fallback handling left users with no way to act on these notifications; purpose-built cases provide clear action paths and match the non-blocking design intent
- Terminal statusline and CLI output use unified label 'chat X%' for per-chat context-window percentage, matching IDE extension display — Both surfaces measure the same metric; using identical labels eliminates user confusion and provides consistent terminology across all UI surfaces
- Quota hard-trigger gates on populated quota_reset_at before firing; if reset_at is unknown (fresh per-session stats file), trigger holds off and retries next poll cycle instead of firing blind with no dedup memory — quota_triggered_windows.json dedup is keyed on quota_reset_at; firing without it present means the dedup guard never engages, causing re-announcement on every poll cycle. Mirrors the soft 75% warning which already gates on reset_at.
- Phase 3.15-S0 (hard context budget cap) is the immediate priority for fixing context-trigger cascade, not the full S1–S7 pipeline — S0 is a minimal, isolated fix that works on today's full-dump injection without depending on S1–S7; it directly prevents new companions from starting with already-high context; S1–S7 can follow after S0 is validated

## Files In Play
- `askr/session/lifecycle.py`

## Relational Files
- `askr/session/post_tool_use.py` (imported_by): Handles usage-API refresh that populates quota_reset_at; the quota-trigger fix depends on understanding when reset_at becomes available
- `askr/session/stop.py` (imported_by): Implements Stop-hook signal logic that determines direction_proposal vs direction_confirm; relevant to Signal 3 gap investigation
- `askr/cli/askr.py` (imported_by): Terminal statusline display; fixed this session to use unified 'chat X%' label
- `extension.js` (configures): IDE extension display; already uses 'chat X%' label; terminal now matches

## Blockers
- Phase 3.13 S2 (rejected_decisions.json persistence) not yet built — blocks Phase 3.15-S4 (rejected-decisions filter)
