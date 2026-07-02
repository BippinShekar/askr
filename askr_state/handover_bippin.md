# Handover: bippin

Last updated: 2026-07-02 11:23

*Source of truth: `handover_bippin.json`*


## Task
Fixed nested git-worktree state directory hijacking by implementing shared find_project_root() helper and adding regression tests to prevent askr_state from being discovered in nested worktrees.

## Discussion
The askr project was vulnerable to a state-directory hijacking bug where a nested git worktree's .claude/askr_state directory could be discovered as the project root, locking out normal navigation. This session refactored get_state_dir() in config.py to use a new shared find_project_root() helper that correctly stops at the primary worktree, added comprehensive unit tests (test_get_state_dir.py) and a regression case in test_pre_tool_use_guard.py, verified the fix live with a test worktree, and confirmed all 128 tests pass. The fix is now in production (commit 4da1fdb).

## Accomplishments
- [x] Refactored get_state_dir() to use shared find_project_root() helper that respects git worktree boundaries
- [x] Created test_get_state_dir.py with unit tests for state directory discovery logic
- [x] Added nested-worktree regression test case to test_pre_tool_use_guard.py
- [x] Verified fix live by creating test worktree and confirming cd .. works without guard blocking
- [x] All 128 tests passing including 3 new tests; committed and pushed as 4da1fdb

## Next Actions
1. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint (trigger_type==emergency branch)
   *Why: Identified in prior sessions; emergency checkpoints currently bypass proper handover serialization*
2. Audit and remove dead code path in guard_runner.py for non-blocking notification.json (type: guard_warning) that is never invoked from pre_tool_use.py or HOOK_MAP
   *Why: Phase 3.5 IDE popup for non-blocking guard warnings cannot fire today; dead code should be cleaned up*

## Decisions
- Implement prevention of nested-worktree state hijacking via shared find_project_root() helper rather than post-hoc detection — True prevention at discovery time is cleaner and more reliable than detecting duplicates after the fact; git worktree is a legitimate use case that must be supported

## Files In Play
- `askr/state/config.py`
- `askr/session/monitor.py`
- `tests/test_get_state_dir.py`
- `tests/test_pre_tool_use_guard.py`

## Relational Files
- `askr/state/config.py` (imports): Contains get_state_dir() which now uses shared find_project_root() helper
- `askr/session/monitor.py` (imports): Updated to use shared find_project_root() helper instead of duplicating logic
- `tests/test_get_state_dir.py` (tested_by): New unit tests for state directory discovery logic
- `tests/test_pre_tool_use_guard.py` (tested_by): Added nested-worktree regression test case to HandleBashTests
