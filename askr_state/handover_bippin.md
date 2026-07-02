# Handover: bippin

Last updated: 2026-07-02 11:22

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions; fixed handover generation bug leaking .claude/ directory noise into uncommitted files list; diagnosed and fixed get_state_dir() fallback vulnerability that could load a different project's stored path, and scrubbed foreign-repo (leaps) contamination from shared state files; reproduced and documented nested worktree cwd-drift lockout as a genuine but collision-specific bug requiring manual escape via absolute paths; clarified that desired architecture supports multi-repo concurrent execution from single terminal session, requiring cross-repo execution guards to remain permissive rather than restrictive; implemented permanent fix for nested git-worktree askr_state hijacking by refactoring get_state_dir() and find_project_root() to always resolve from current working directory upward without cross-project fallback, and added comprehensive regression test coverage.

## Discussion
Session completed the nested worktree lockout fix that prior sessions had diagnosed but deferred. The root cause was get_state_dir() and find_project_root() falling back to cached or global state when the current project had no stored path, allowing a nested worktree's askr_state to hijack the parent project's root resolution. The fix refactored both functions to always walk upward from cwd without fallback, eliminating cross-project contamination entirely. This preserves the desired multi-repo concurrent execution architecture (spawning askr tasks in one repo while working in another from the same terminal) by keeping guards permissive while ensuring each project's state directory is resolved independently. All 128 tests pass including 3 new regression tests that verify the nested-worktree scenario is fixed and guard behavior remains correct.

## Accomplishments
- [x] Scoped voice notification feature: confirmed macOS-only deployment enables native `say` TTS without cross-platform abstraction
- [x] Identified notification hook integration points (askr/hooks/stop.py, notification.py) for wiring voice updates as additional sink alongside Discord
- [x] Designed voice notification preference schema: machine-level boolean flag stored in global ~/.config/askr/config.json (not per-project)
- [x] Implemented load_voice_enabled() and save_voice_enabled() helper functions in askr/state/config.py following existing config pattern
- [x] Diagnosed handover generation bug: _get_uncommitted_files() in checkpoint.py dumping raw git status output without .claude/ filtering
- [x] Fixed checkpoint.py to exclude .claude/ directory from uncommitted files list in handover documents
- [x] Verified no active nested worktree lockout condition at session start; prior session's guard collision was event-specific, not standing bug
- [x] Deliberately reproduced nested worktree cwd-drift lockout by creating test worktree at .claude/worktrees/repro-test and confirming cd/pwd/ls fail when cwd is inside nested worktree's askr_state
- [x] Confirmed nested worktree lockout can be escaped via absolute paths (/bin/pwd) or relative traversal (cd ./../../..)
- [x] Discovered critical security issue: get_state_dir() could fall back to loading a different project's stored path from ~/.config/askr/config.json if current project had no stored path
- [x] Fixed get_state_dir() to always return the current project's state directory without cross-project fallback contamination
- [x] Refactored find_project_root() to walk upward from cwd without global fallback, ensuring nested worktrees cannot hijack parent project root resolution
- [x] Updated monitor.py to use refactored find_project_root() helper for consistent project root discovery across all session monitoring code
- [x] Created test_get_state_dir.py with unit tests for get_state_dir() and find_project_root() covering normal project, nested worktree, and cross-project contamination scenarios
- [x] Added nested-worktree regression test case to test_pre_tool_use_guard.py's HandleBashTests class to verify guard behavior remains correct when cwd is inside nested worktree
- [x] Ran full test suite: all 128 tests pass including 3 new regression tests for nested worktree and get_state_dir() fixes
- [x] Verified nested worktree lockout is permanently fixed by creating live test worktree, confirming cd .. now works instead of being blocked
- [x] Committed fix with decision log: get_state_dir() and find_project_root() now always resolve from cwd upward without cross-project fallback

## Next Actions
1. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate (checkpoint.py create_checkpoint, trigger_type==emergency branch)
   *Why: Open goal from prior sessions; emergency handovers currently bypass the full handover generation pipeline*
2. Investigate guard_runner.py's non-blocking notification.json path (type: guard_warning) dead code — verify it is never invoked from pre_tool_use.py, HOOK_MAP, or .claude/settings.json, and document or remove if confirmed unused
   *Why: Open goal; Phase 3.5's IDE popup for non-blocking guard warnings cannot fire today regardless of extension.js whitelist fix, suggesting this code path may be orphaned*
3. Integrate voice notification feature into askr init flow and Discord notification hooks to complete the macOS TTS opt-in system
   *Why: Voice notification feature is designed and partially implemented but not yet wired into the actual notification pipeline*

## Decisions
- Voice notification feature is macOS-only, using native `say` command without cross-platform abstraction — Simplifies implementation and deployment; macOS users get native TTS without adding external dependencies or platform-specific complexity
- Voice notification preference is stored as machine-level boolean in ~/.config/askr/config.json, not per-project — User preference for spoken updates is a machine-wide setting, not project-specific; centralizing in global config avoids duplication
- get_state_dir() and find_project_root() must always walk upward from current working directory without global or cached fallback — Prevents nested git-worktrees from hijacking parent project root resolution; ensures each project's state is resolved independently, supporting multi-repo concurrent execution from single terminal session
- Cross-repo execution guards remain permissive rather than restrictive to support multi-repo concurrent execution architecture — System must allow spawning askr tasks in one repo while actively working in another from the same terminal; restrictive project-root-based locking would block this capability

## Failed Approaches
- Implementing project-root-based path locking to prevent nested worktree cwd-drift lockout — Conflicts with desired architecture: system must support multi-repo concurrent execution from single terminal, which requires cross-repo execution guards to be permissive rather than restrictive

## Files In Play
- `askr/state/config.py`
- `askr/session/monitor.py`
- `tests/test_get_state_dir.py`
- `tests/test_pre_tool_use_guard.py`

## Relational Files
- `askr/session/checkpoint.py` (imports|configures): Contains _get_uncommitted_files() that was fixed to exclude .claude/ directory; uses get_state_dir() for state directory resolution
- `askr/session/pre_tool_use.py` (imports): Invokes pre_tool_use guard logic that depends on find_project_root() for guard collision detection
- `askr/hooks/stop.py` (configures): Identified as integration point for voice notification feature alongside Discord notifications
- `askr/notification.py` (configures): Identified as integration point for voice notification feature; will wire voice updates as additional sink
- `tests/test_pre_tool_use_guard.py` (tested_by): Contains HandleBashTests class with new nested-worktree regression test case verifying guard behavior

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
