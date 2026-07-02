# Handover: bippin

Last updated: 2026-07-02 11:27

*Source of truth: `handover_bippin.json`*


## Task
Fixed nested git-worktree state directory hijacking and routed PreCompact emergency handovers through the real LLM path instead of hardcoded boilerplate.

## Discussion
The askr project addressed two critical bugs: (1) a state-directory hijacking vulnerability where nested git worktrees' .claude/askr_state could be discovered as the project root, fixed by refactoring get_state_dir() to use a shared find_project_root() helper that respects worktree boundaries; (2) emergency (PreCompact) checkpoints that bypassed proper handover serialization and had a latent UnboundLocalError for transcript_text, fixed by routing them through the real _generate_handover_with_llm() path in checkpoint.py. Both fixes are now in production with comprehensive test coverage (131 tests passing).

## Accomplishments
- [x] Refactored get_state_dir() to use shared find_project_root() helper that respects git worktree boundaries
- [x] Created test_get_state_dir.py with unit tests for state directory discovery logic
- [x] Added nested-worktree regression test case to test_pre_tool_use_guard.py
- [x] Verified nested-worktree fix live by creating test worktree and confirming cd .. works without guard blocking
- [x] Routed PreCompact emergency handovers through real LLM path in checkpoint.py instead of hardcoded boilerplate
- [x] Created test_checkpoint_emergency.py regression test proving emergency checkpoints call real handover serialization
- [x] All 131 tests passing including 5 new tests; committed as 4da1fdb and b89e588

## Next Actions
1. Audit and remove dead code path in guard_runner.py for non-blocking notification.json (type: guard_warning) that is never invoked from pre_tool_use.py or HOOK_MAP
   *Why: Phase 3.5 IDE popup for non-blocking guard warnings cannot fire today; dead code should be cleaned up to reduce maintenance surface*

## Decisions
- Implement prevention of nested-worktree state hijacking via shared find_project_root() helper rather than post-hoc detection — True prevention at discovery time is cleaner and more reliable than detecting duplicates after the fact; git worktree is a legitimate use case that must be supported
- Route emergency (PreCompact) handovers through real _generate_handover_with_llm() path instead of hardcoded boilerplate string — Ensures emergency checkpoints produce proper JSON handover documents with full context serialization; eliminates latent UnboundLocalError bug in transcript_text assignment

## Files In Play
- `askr/session/checkpoint.py`
- `tests/test_checkpoint_emergency.py`

## Relational Files
- `askr/session/checkpoint.py` (imports): Contains create_checkpoint() which now routes emergency trigger_type through real LLM handover path
- `tests/test_checkpoint_emergency.py` (tested_by): New regression test proving emergency checkpoints call real handover serialization and produce valid JSON
- `askr/state/writer.py` (imports): Contains _generate_handover_with_llm() which is now called for emergency checkpoints

## Uncommitted Files
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`
