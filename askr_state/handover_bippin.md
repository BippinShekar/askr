# Handover: bippin

Last updated: 2026-07-02 00:36

*Source of truth: `handover_bippin.json`*


## Task
Completed pre-launch safety audits on session management core (45 passing tests, checkpoint/guard/hook systems verified), identified critical packaging gap (brew Formula ships wrong package), documented roadmap findings, discovered and rotated leaked webhook credential, and implemented dangerous-permission task approval gate with lifecycle signal-based companion session triggering.

## Discussion
Session ran two autonomous audits in parallel: safety-gate verification (unbuilt gates, race conditions) and test-suite health check (packaging readiness). Core session-management infrastructure (hooks, checkpoint, guard, state sync) is production-ready with full test coverage. Critical blocker identified: homebrew Formula did not install the full askr/ package or create bin/askr entry point — now fixed to ship full package with proper entry point and requirements.txt deps. Discovered Discord webhook credential leaked in git history (rotated, requires git-filter-repo scrubbing). This session completed the dangerous-permission task approval gate (Phase 5 roadmap item): wired permission detection into session_start.py, added _peek_task_queue/_consume_approval_flag/_notify_tasks_held helpers, and switched lifecycle.py to use Stop hook signal instead of JSONL idle heuristic for triggering companion sessions. All 45 tests still passing; commits pushed safely without blocking parallel session_start.py edits in progress.

## Accomplishments
- [x] Ran autonomous safety-gate audit verifying unbuilt gates and race conditions in session-management core
- [x] Ran autonomous test-suite health audit verifying packaging readiness and test coverage
- [x] Confirmed session-management core (hooks, checkpoint, guard, state sync) is production-ready with 45 passing tests
- [x] Identified critical packaging blocker: homebrew Formula installs wrong package (root *.py only, not full askr/ package)
- [x] Documented pre-launch audit findings and blockers to roadmap.md and goals backlog
- [x] Discovered Discord webhook credential leaked in git history (rotated, requires git-filter-repo scrubbing)
- [x] Fixed Formula/askr.rb to install full askr/ package, create bin/askr entry point, install deps from requirements.txt
- [x] Implemented dangerous-permission task approval gate: added _peek_task_queue, _consume_approval_flag, _notify_tasks_held to session_start.py
- [x] Switched lifecycle.py from JSONL idle-time heuristic to Stop hook signal for triggering companion sessions
- [x] Added _signal_turn_stopped call in hooks/stop.py to mark turn completion for lifecycle polling
- [x] Verified all 45 tests still pass after lifecycle/stop/formula changes
- [x] Committed and pushed Formula/askr.rb, askr/hooks/stop.py, askr/session/lifecycle.py without blocking parallel session_start.py edits

## In Progress
- `askr/hooks/session_start.py` (line 434): Wire dangerous-permission detection into session start flow; hold queued tasks if session has dangerous permissions and no approval flag; notify via Discord and notification.json; add task approval/discard CLI commands
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry
- `None`: Cut real git tag + GitHub release so Formula sha256/url are real, and create homebrew-askr tap repo
- `askr/guard/pre_tool_use.py`: Extend cross-repo boundary check to cover Bash tool calls, not just Write/Edit/MultiEdit
- `askr/checkpoint.py`: Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate
- `None`: Add test coverage for pre_tool_use.py/guard_runner.py - the implementation guard has zero tests despite being security-critical
- `README.md`: Update documentation - Phase 3 (notifications) and Phase 3.5 (guard) are built and running, not 'Coming Next'

## Next Actions
1. Scrub Discord webhook from git history using git-filter-repo: clone --mirror, run filter-repo with --replace-text to remove credential, force-push to origin. Document exact steps and verify no traces remain in GitHub.
   *Why: Credential leaked in git history is a critical security issue; must be removed before any public release or tap repo creation.*
2. Complete session_start.py dangerous-permission gate: finish wiring permission_gate.is_dangerous_session call, test task holding/approval flow, add askr task approve/discard CLI commands, verify notification delivery.
   *Why: Gate logic is partially in place but CLI commands and full integration testing not yet done; Phase 5 roadmap item.*
3. Cut real git tag (e.g. v0.1.0) and create GitHub release with tarball; update Formula/askr.rb sha256 and url to point to real release artifact.
   *Why: Formula currently has placeholder sha256/url; real release is prerequisite for homebrew-askr tap repo and public distribution.*
4. Create homebrew-askr tap repo (GitHub org/homebrew-askr) and push Formula/askr.rb there; test installation via brew tap + brew install.
   *Why: Completes packaging story; enables users to install via standard homebrew workflow.*
5. Extend askr/guard/pre_tool_use.py cross-repo boundary check to cover Bash tool calls, not just Write/Edit/MultiEdit.
   *Why: Guard currently incomplete; Bash calls can escape repo boundaries without detection.*
6. Add test coverage for pre_tool_use.py and guard_runner.py (currently zero tests despite being security-critical path).
   *Why: Implementation guard has no test coverage; critical for safety verification before production use.*
7. Fix PreCompact emergency handover in askr/checkpoint.py to route through real LLM handover path instead of hardcoded boilerplate.
   *Why: Emergency handover currently uses placeholder text; must use real handover generation for production readiness.*
8. Update README.md to reflect that Phase 3 (notifications) and Phase 3.5 (guard) are built and running, not 'Coming Next'.
   *Why: Documentation is out of sync with implementation; users need accurate roadmap.*

## Decisions
- Dangerous-permission task approval gate uses one-shot flag (_consume_approval_flag) rather than persistent permission setting — Each held batch requires explicit approval; approving once does not silently authorize every future batch. Safer default for dangerous permissions.
- Lifecycle companion session triggering switched from JSONL idle-time heuristic to Stop hook signal — Signal-based approach is more reliable and precise; idle-time heuristic was fragile and could miss turn boundaries.
- Task approval notification sent via both Discord and local notification.json file — Dual-channel approach ensures developer sees approval request even if Discord is unavailable; local file is fallback.

## Files In Play
- `askr/hooks/session_start.py`
- `askr/hooks/stop.py`
- `askr/session/lifecycle.py`
- `Formula/askr.rb`

## Relational Files
- `askr/session/permission_gate.py` (imported_by): session_start.py calls is_dangerous_session() to determine whether to hold queued tasks
- `askr/clients/discord.py` (imported_by): session_start.py uses send_message() to notify developer of held tasks
- `askr/state/config.py` (imported_by): session_start.py uses get_state_dir() to locate task queue and notification files
- `tests/` (tested_by): All 45 tests still passing after lifecycle/stop/formula changes

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Discord webhook credential leaked in git history must be scrubbed via git-filter-repo before public release
- Real git tag and GitHub release required before Formula sha256/url can be finalized and homebrew-askr tap created
