# Handover: bippin

Last updated: 2026-06-19 03:38

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed 5 critical daemon stability fixes, resolved session-stats tracking to use explicit session_id instead of mtime-based guessing, fixed cmd_team() display to read from correct queue_<dev>.jsonl format, validated daemon stability and task-queue delivery mechanism, investigated state file architecture, added integration test coverage for askr init launchd idempotency, diagnosed and resolved recurring stats-indicator error in Cursor status-line extension by removing per-project hash filtering and reverting to global newest-stats-file lookup, and fixed terminal statusline 0% display issue.

## Discussion
The recurring "disappearing stats error" in the Cursor status-line extension was caused by hardcoded per-project stats path logic that became stale after stats consolidation. This session completed the fix by removing the `projectHashPrefix()` and `projectStatsPath()` filtering entirely from extension.js, reverting to a simpler global "newest stats file by mtime" model that worked before refactoring. A secondary issue — the statusline showing fake 0% before the first message — was fixed by preventing stats display until a real stats file exists. Both fixes are committed (11751ed), tests pass, and the extension is ready for reinstall.

## Accomplishments
- [x] Diagnosed and fixed companion-open premature trigger: changed from context_pct >= CONTEXT_TRIGGER heuristic to waiting for actual Stop-hook turn-end signal in lifecycle.py
- [x] Made askr init idempotent: _install_launchd now checks daemon health before reloading, skipping unnecessary launchd restarts
- [x] Consolidated stats tracking: removed legacy per-project stats files, unified to single session-scoped cost tracking in cost.py
- [x] Purged stale off-topic content from handover_bippin.json (Leaps fundraising details, KAE Capital outreach, PI Ventures strategy) that had accumulated from prior sessions
- [x] Added git tracking rules to .gitignore for .askr_history and notifications.log to prevent log pollution
- [x] Added prevention rule to checkpoint.py to block future off-topic content accumulation in handover documents
- [x] Validated daemon.log for relaunch-loop recurrence after the 5 fixes; confirmed daemon stable (PID 99310, running since 01:17 AM) with single companion-open trigger and correct dedup suppression of repeat spawns
- [x] Reviewed lifecycle.py companion-open logic and companioned_sessions dedup tracking; confirmed design is correct and working as intended
- [x] Investigated task-queue delivery mechanism: confirmed session_start.py correctly loads pending tasks via _load_pending_tasks() hook, independent of broken `askr team` display; no dangling references to deleted per-project stats files in session_start.py
- [x] Refactored session-stats tracking to use explicit session_id instead of mtime-based guessing: updated get_session_stats() in monitor.py to accept optional session_id parameter, wired through post_tool_use.py and session_start.py call sites to pass real session_id, eliminating race condition in multi-session scenarios
- [x] Fixed cmd_team() display command: corrected queue file lookup from queue_<dev>.md to queue_<dev>.jsonl in cli/askr.py line 1444, enabling proper task display for users
- [x] Investigated state file architecture: confirmed goals.jsonl, decisions.jsonl, and implementation_*.jsonl are actively used by reader.py and checkpoint.py for session-scoped state persistence
- [x] Removed per-project stats path filtering from IDE extension: deleted projectHashPrefix() and projectStatsPath() functions from extension.js, reverted to global newest-stats-file lookup by mtime in ~/.config/askr/stats/
- [x] Fixed terminal statusline 0% display issue: added guard in askr.py to prevent stats display until a real stats file exists, eliminating fake 0% indicator before first message

## Next Actions
1. Reload the Cursor window to pick up the new extension.js from source (or reinstall via `askr init` if extension copy is not auto-synced)
   *Why: The extension fix is committed but the IDE is still running the old version with per-project filtering; reload is required for the new global stats lookup to take effect*
2. Verify the statusline now displays correct cost % (not 0%) and no longer shows the disappearing stats error after reload
   *Why: Confirm both fixes (extension stats lookup + 0% guard) are working in the live IDE*
3. Monitor daemon.log and extension behavior over the next few sessions to ensure no regression in stats tracking or statusline display
   *Why: This was a recurring issue; sustained validation will confirm the root cause was truly the per-project filtering logic*

## Decisions
- Revert IDE extension stats lookup from per-project hash filtering to global newest-stats-file model — Per-project filtering became stale after stats consolidation refactored the stats architecture; global lookup is simpler, more robust, and matches the current single-session-scoped stats design
- Guard statusline stats display to prevent showing 0% before a real stats file exists — Fake 0% indicator was confusing and misleading; only display stats once cost.py has written a real stats file

## Files In Play
- `askr/ide/vscode-extension/extension.js`
- `askr/cli/askr.py`

## Relational Files
- `askr/hooks/post_tool_use.py` (imported_by): Calls get_session_stats() with explicit session_id; part of stats tracking refactor
- `askr/session/monitor.py` (imported_by): Defines get_session_stats() that now accepts optional session_id parameter
- `askr/hooks/session_start.py` (imported_by): Calls get_session_stats() and loads pending tasks; verified no stale stats references
- `askr/session/lifecycle.py` (configures): Contains companion-open trigger logic; reviewed and confirmed correct
- `askr/hooks/checkpoint.py` (configures): Added prevention rule to block off-topic content accumulation in handover documents
- `.gitignore` (configures): Added rules for .askr_history and notifications.log to prevent log pollution

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
