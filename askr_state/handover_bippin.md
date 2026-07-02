# Handover: bippin

Last updated: 2026-07-02 10:38

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions; fixed handover generation bug leaking .claude/ directory noise into uncommitted files list; diagnosed and fixed get_state_dir() fallback vulnerability that could load a different project's stored path, and scrubbed foreign-repo (leaps) contamination from shared state files; reproduced and documented nested worktree cwd-drift lockout as a genuine but collision-specific bug requiring manual escape via absolute paths; identified project root storage as potential fix for nested worktree lockout but deferred implementation pending security review of askr_state/.gitignore exposure and cross-repo execution model clarification.

## Discussion
Session focused on deliberately reproducing the nested worktree lockout condition to confirm it is a genuine bug, not a phantom collision artifact. Successfully created a test worktree at .claude/worktrees/repro-test and confirmed that cd into the nested worktree's askr_state directory blocks normal navigation (cd .., pwd, ls all fail with permission/path errors) but can be escaped via absolute paths (/bin/pwd) or relative traversal (cd ./../../..). User proposed storing absolute project root during askr init as a fix and clarified that the desired architecture is to support multi-repo concurrent execution from a single terminal session (e.g., spawning askr tasks in the leaps repo while actively working in askr repo), which requires cross-repo execution guards to be permissive rather than restrictive. This architectural intent conflicts with the direct implementation of project-root-based path locking and requires rethinking the guard strategy before proceeding.

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
- [x] Scrubbed 7 lines of foreign-repo (leaps) contamination from askr_state/failed_approaches.md that had leaked into shared state tracking
- [x] Updated project memory (project_handover_repo_scoping.md and MEMORY.md) to reflect corrected understanding of nested worktree behavior and cross-repo execution requirements
- [x] Clarified architectural intent: user wants to spawn concurrent askr tasks across multiple repos (leaps, askr) from a single terminal session, requiring permissive cross-repo execution guards rather than restrictive path locking

## Next Actions
1. Audit guard_runner.py and pre_tool_use.py cross-repo write guards to understand current blocking logic and identify which guards must be relaxed to support multi-repo concurrent execution
   *Why: User's architectural intent (spawn askr tasks in leaps repo while working in askr repo) directly conflicts with current restrictive guard strategy; must map guard behavior before implementing project-root storage fix*
2. Design cross-repo execution model: define which operations should be repo-scoped (state isolation, config isolation) vs. which should be global (voice notifications, session tracking) to enable safe multi-repo concurrency
   *Why: Current nested worktree lockout is a symptom of overly strict path validation; fixing it requires explicit architectural decision about repo boundaries and shared state*
3. Implement project-root storage in askr init (store absolute path in project-local askr_state/config.json, not global ~/.config/askr/config.json) after guard audit clarifies safety constraints
   *Why: This is the proposed fix for nested worktree lockout, but must be implemented with awareness of cross-repo execution model to avoid recreating the fallback contamination bug*
4. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate (checkpoint.py create_checkpoint, trigger_type==emergency branch)
   *Why: Open goal from prior session; emergency checkpoints currently bypass proper decision logging and context preservation*
5. Investigate guard_runner.py's non-blocking notification.json path (type: guard_warning) dead code and determine if Phase 3.5 IDE popup feature should be removed or completed
   *Why: Open goal from prior session; code path is never invoked and extension.js whitelist fix cannot enable it without implementation work*

## Decisions
- Voice notifications are macOS-only feature, no cross-platform abstraction required — Simplifies implementation, leverages native `say` command, acceptable for initial release
- Voice notification preference stored globally in ~/.config/askr/config.json, not per-project — User preference is machine-level, not project-specific; consistent with other global config patterns
- Nested worktree cwd-drift lockout is a genuine bug, not a phantom collision artifact — Reproducible with clean test worktree setup; occurs when cwd is inside nested worktree's askr_state directory
- get_state_dir() must not fall back to a different project's stored path; always return current project's state directory — Cross-project fallback is a critical security vulnerability that can leak state between unrelated repos
- Project-root storage as fix for nested worktree lockout is architecturally sound but requires guard audit before implementation — User's multi-repo concurrent execution intent conflicts with overly restrictive path-based guards; must clarify which operations are repo-scoped vs. global before locking paths

## User-Rejected Approaches
- **Direct implementation of project-root storage to fix nested worktree lockout by storing absolute path in global config** — "User clarified that the desired architecture is to support multi-repo concurrent execution (spawn askr tasks in leaps repo while working in askr repo), which requires cross-repo execution guards to be permissive rather than restrictive" (domain: askr/state/config.py, guard_runner.py, pre_tool_use.py)

## Failed Approaches
- Storing project root in global ~/.config/askr/config.json as direct fix for nested worktree lockout — This recreates the fallback contamination bug that was just fixed (get_state_dir() loading a different project's path); requires project-local storage instead, but that conflicts with current guard strategy until cross-repo execution model is clarified

## Files In Play
- `askr/state/config.py`
- `askr/checkpoint.py`
- `askr/hooks/stop.py`
- `askr/notification.py`
- `askr/guard_runner.py`
- `askr/pre_tool_use.py`
- `askr_state/failed_approaches.md`
- `askr_state/MEMORY.md`

## Relational Files
- `askr/checkpoint.py` (imports): Handover generation bug fix (_get_uncommitted_files filtering .claude/) is in this file
- `askr/hooks/stop.py` (imported_by): Voice notification integration point for task completion announcements
- `askr/notification.py` (imported_by): Voice notification integration point for session state transitions
- `askr/guard_runner.py` (configures): Cross-repo write guards that must be audited before implementing project-root storage fix
- `askr/pre_tool_use.py` (configures): Guard hook invocation logic that must be audited for multi-repo execution model
- `.gitignore` (configures): askr_state/.gitignore exposure is a security concern for project-root storage implementation

## Blockers
- Cross-repo execution model must be clarified before implementing project-root storage fix; current guard strategy is overly restrictive for user's desired multi-repo concurrent execution architecture
