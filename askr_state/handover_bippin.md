# Handover: bippin

Last updated: 2026-06-19 01:17

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed 5 critical daemon stability fixes (companion-open deferral, idempotent init, stats file consolidation, handover cleanup, git tracking) to resolve context-overflow and relaunch-loop issues in the askr daemon lifecycle.

## Discussion
This session focused entirely on codebase stability and daemon reliability. User identified and fixed a cascade of issues: companion-open was triggering prematurely on context% heuristics rather than actual turn-end signals, causing relaunch loops; askr init was non-idempotent and reloading launchd unnecessarily; stats tracking was fragmented across per-project files creating stale state; and handover documents were accumulating off-topic business content (Leaps fundraising details) that never got cleaned up. All 5 fixes were implemented, tested, committed, and pushed. The session also added prevention rules to checkpoint.py to block future off-topic content accumulation.

## Accomplishments
- [x] Diagnosed and fixed companion-open premature trigger: changed from context_pct >= CONTEXT_TRIGGER heuristic to waiting for actual Stop-hook turn-end signal in lifecycle.py
- [x] Made askr init idempotent: _install_launchd now checks daemon health before reloading, skipping unnecessary launchd restarts
- [x] Consolidated stats tracking: removed legacy per-project stats files, unified to single session-scoped cost tracking in cost.py
- [x] Purged stale off-topic content from handover_bippin.json (Leaps fundraising details, KAE Capital outreach, PI Ventures strategy) that had accumulated from prior sessions
- [x] Added git tracking rules to .gitignore for .askr_history and notifications.log to prevent log pollution
- [x] Added prevention rule to checkpoint.py to block future off-topic content accumulation in handover documents

## Next Actions
1. Monitor daemon.log for relaunch-loop recurrence after the 5 fixes; if companion-open still triggers unexpectedly, add debug logging to lifecycle.py _execute_trigger() to trace signal flow
   *Why: Fixes are deployed but real-world daemon behavior under load needs validation; context-overflow symptoms may have secondary causes*
2. Review session_start.py _reset_stats_for_project() to confirm it no longer references deleted per-project stats files
   *Why: Stats consolidation removed files but callers may still reference them, causing silent failures*
3. Add integration test for askr init idempotency: verify daemon stays healthy and launchd is not reloaded on second init call
   *Why: Idempotency fix is critical for CI/CD and user re-runs; needs automated coverage*

## Decisions
- Removed all Leaps/fundraising/KAE Capital/PI Ventures content from project state documents — Off-topic business strategy content does not belong in codebase handover; it accumulates and pollutes future sessions' context
- Consolidated stats tracking to single session-scoped file instead of per-project files — Per-project stats files created stale state and fragmented cost tracking; session-scoped approach is simpler and matches daemon lifecycle
- Changed companion-open trigger from context% heuristic to actual Stop-hook signal — Context% is unreliable and context-dependent; Stop-hook provides definitive turn-end signal that prevents premature relaunch

## Failed Approaches
- Using context_pct >= CONTEXT_TRIGGER as signal for companion-open in lifecycle.py — Heuristic was unreliable and context-dependent; caused premature relaunch loops when context filled up mid-session
- Maintaining per-project stats files alongside session-scoped cost tracking — Created fragmented state, stale files, and confusion about which file was source of truth; consolidated to single session-scoped approach
- Allowing off-topic business content in handover documents — Content never gets cleaned up automatically and reappears in every future session, polluting context and violating project state document purpose

## Files In Play
- `askr/session/lifecycle.py`
- `askr/cli/askr.py`
- `askr/hooks/session_start.py`
- `askr/session/checkpoint.py`
- `askr/session/cost.py`
- `.gitignore`

## Relational Files
- `askr/hooks/stop.py` (imported_by): Provides Stop-hook signal that lifecycle.py now waits for instead of context% heuristic
- `askr/ide/vscode-extension/extension.js` (configures): Calls get_session_cost_summary(); needs to reference consolidated cost.py, not deleted per-project stats files
- `askr/hooks/pre_compact.py` (imported_by): Checkpoint logic that now includes prevention rule for off-topic content
