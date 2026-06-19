# Handover: bippin

Last updated: 2026-06-19 14:40

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed 5 critical daemon stability fixes, resolved session-stats tracking to use explicit session_id instead of mtime-based guessing, fixed cmd_team() display to read from correct queue_<dev>.jsonl format, validated daemon stability and task-queue delivery mechanism, investigated state file architecture, added integration test coverage for askr init launchd idempotency, diagnosed and resolved recurring stats-indicator error in Cursor status-line extension by removing per-project hash filtering and reverting to global newest-stats-file lookup, fixed terminal statusline 0% display issue, removed erroneous stats file deletion in stop.py that was clearing session state on every turn-end, conducted codebase audit to assess team-management feature scope and test coverage, reviewed team-management initialization flow and co-founder collaboration readiness, confirmed solo-developer initialization is production-ready with 41/41 tests passing and clean idempotent askr init flow, verified context-percentage display accuracy in cost tracking, investigated context-window cutoff threshold for companion-open triggering, validated that 60% context-trigger threshold is intentional (40% runway buffer against extended-thinking spikes) with potential adjustment to 65% warranting further testing, investigated webhook global state persistence and uninstall isolation for multi-repo co-founder initialization, clarified uninstall safety (repo-scoped, does not delete global files) and webhook-global-none display behavior (by design: each repo init checks for pre-existing global webhook, displays none if not found in this repo's context), and identified four critical blockers for multi-repo co-founder collaboration: end-to-end team-add + queue + execution test, proper queue-drain system, permission isolation (co-founder tasks drained per his Claude permissions, not overwritten by initiator), and git state handling for shared repo.

## Discussion
Solo-developer initialization is production-ready: 41/41 tests pass, askr init flow is clean with proper fallbacks at every LLM-call boundary, and daemon stability has been validated. Co-founder collaboration features are partially implemented—team-add flow exists but lacks integration tests and multi-dev state synchronization. Context-percentage display is accurate; the 60% context-trigger threshold is a deliberate design choice with 40% runway to survive extended-thinking spikes; 65% threshold may improve usability but requires testing. Uninstall is repo-scoped and safe for multi-repo initialization. Webhook global state is persistent across repos but each repo's init displays webhook-global status relative to that repo's context. User identified a critical architectural gap: architecture.md and project_brief.md are gitignored (local, machine-tied, regenerated per checkpoint) but are not in .gitattributes, creating false confidence that they are shared state when they are not—this breaks the assumption that co-founder can rely on shared documentation and requires explicit design decision on how shared state is managed across repos.

## Accomplishments
- [x] Diagnosed and fixed companion-open premature trigger: changed from context_pct >= CONTEXT_TRIGGER heuristic to waiting for actual Stop-hook turn-end signal in lifecycle.py
- [x] Made askr init idempotent: _install_launchd now checks daemon health before reloading, skipping unnecessary launchd restarts
- [x] Consolidated stats tracking: removed legacy per-project stats files, unified to single session-scoped cost tracking in cost.py
- [x] Purged stale off-topic content from handover_bippin.json (Leaps fundraising details, KAE Capital outreach, PI Ventures strategy) that had accumulated from prior sessions
- [x] Added git tracking rules to .gitignore for .askr_history and notifications.log to prevent log pollution
- [x] Added prevention rule to checkpoint.py to block future off-topic content accumulation in handover documents
- [x] Identified architectural gap: architecture.md and project_brief.md are gitignored (local, machine-tied) but not in .gitattributes, creating false shared-state assumption for co-founder multi-repo collaboration
- [x] Confirmed uninstall is repo-scoped and safe for multi-repo co-founder initialization; verified webhook global state persistence and per-repo context-relative display behavior

## In Progress
- `None`: Design decision: how to handle shared state (architecture.md, project_brief.md) across co-founder repos—currently local/gitignored but user expects them to be shared

## Next Actions
1. Decide: should architecture.md and project_brief.md be shared (committed to git, synced across co-founder machines) or remain local (each dev regenerates on checkpoint)? If shared, add to .gitattributes with merge strategy; if local, document this explicitly in README and team-init flow.
   *Why: Current state is ambiguous—files are gitignored but user expects them to be shared state for co-founder collaboration. This blocks confidence in multi-repo initialization.*
2. Write end-to-end integration test: team-add (initiator adds co-founder), queue task for co-founder, co-founder executes task, verify task drains from queue and result is visible to both. File: tests/test_team_e2e.py
   *Why: Zero test coverage for team-add + queue + execution flow. This is the first hard blocker for multi-repo co-founder collaboration.*
3. Implement proper queue-drain system: define drain semantics (FIFO, priority, per-dev isolation), add drain logic to lifecycle.py or new queue_drain.py, ensure co-founder tasks are drained only by co-founder's Claude session (not overwritten by initiator).
   *Why: Second blocker: queue currently has no drain mechanism. Co-founder tasks must be isolated per Claude permissions.*
4. Design and document git state handling for shared repo: clarify which files are co-founder-shared (queue_*.jsonl, goals.jsonl, checkpoint.jsonl) vs. local (architecture.md, project_brief.md, cost tracking), add conflict-resolution strategy to README.
   *Why: Fourth blocker: git merge conflicts and state divergence will occur in shared repo without explicit design. Co-founder needs to know which files to expect to conflict and how to resolve.*
5. Add .gitattributes entries for queue_*.jsonl, goals.jsonl, checkpoint.jsonl with merge strategy (union or custom) to prevent silent data loss in co-founder repos.
   *Why: Shared state files need explicit merge handling to avoid losing tasks or goals when both devs commit simultaneously.*

## Decisions
- 60% context-trigger threshold for companion-open is intentional, not a bug — Provides 40% runway buffer to survive extended-thinking spikes without premature companion open
- Uninstall is repo-scoped and does not delete global files or affect other repos — Safe for multi-repo co-founder initialization; each repo can uninstall independently
- Webhook global state is persistent across repos; each repo's init displays webhook-global status relative to that repo's context — By design: webhook is global but each repo checks for pre-existing global webhook in its own context

## Failed Approaches
- Assumed architecture.md and project_brief.md are shared state because they are in askr_state/ directory — User caught that both files are gitignored (local, machine-tied, regenerated per checkpoint) but not in .gitattributes, creating false confidence in shared state

## Files In Play
- `askr/session/lifecycle.py`
- `askr/cli/askr.py`
- `askr/session/cost.py`
- `askr/session/checkpoint.py`
- `.gitignore`
- `.gitattributes`
- `tests/test_init_idempotency.py`

## Relational Files
- `askr/session/checkpoint.py` (configures): Regenerates architecture.md and project_brief.md on every checkpoint; needs decision on shared vs. local state
- `askr/cli/askr.py` (imports): Contains cmd_team() and team-add flow; needs end-to-end test coverage and queue-drain integration
- `askr/session/lifecycle.py` (configures): Contains CONTEXT_TRIGGER threshold and companion-open logic; also where queue-drain system should integrate
- `.gitattributes` (configures): Needs entries for shared state files (queue_*.jsonl, goals.jsonl, checkpoint.jsonl) to prevent merge conflicts in co-founder repos
- `tests/test_team_e2e.py` (tested_by): Does not exist; needs to be created for end-to-end team-add + queue + execution test

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- End-to-end integration test for team-add + queue + execution does not exist (zero test coverage)
- Proper queue-drain system not implemented; co-founder tasks have no isolation mechanism
- Permission isolation not enforced: co-founder tasks must be drained per his Claude permissions, not overwritten by initiator
- Git state handling for shared repo undefined: no explicit design for which files are co-founder-shared vs. local, no conflict-resolution strategy
- Architectural ambiguity: architecture.md and project_brief.md are gitignored (local, machine-tied) but user expects them to be shared state for co-founder collaboration
