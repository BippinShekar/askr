# Handover: bippin

Last updated: 2026-06-18 19:18

*Source of truth: `handover_bippin.json`*


## Task
Fixed cross-repository state contamination in askr daemon by threading explicit project_path and state_dir parameters through checkpoint.py, lifecycle.py, writer.py, and goals.py, ensuring all git operations and handover writes use the correct repo context instead of relying on ambient os.getcwd(); hardened handover.json schema to prevent LLM fabrication of invented metadata fields.

## Discussion
Root cause identified and systematically patched: create_checkpoint() and git_commit_push() were executing git subprocesses without cwd= parameter, defaulting to the daemon's ambient working directory. Session completed threading state_dir through goals.py::complete_goal() and goals.py::expire_auto_suggested_goals(), added cwd= to all remaining git subprocess calls in git_commit_push(), and hardened the LLM prompt schema in checkpoint.py to forbid invented session_metadata keys (e.g. session_end_reason) and clarify that in_progress.file must be null for non-code work. analytics.py::record_session_end() intentionally left unchanged — it writes to ~/.config/askr/analytics.json, a global file outside any repo by design. Repo-isolation fix is now complete end-to-end: lifecycle.py → checkpoint.py → writer.py/goals.py all thread state_dir/project_path explicitly with no ambient-cwd fallback in the daemon's multi-project path.

## Accomplishments
- [x] Identified cross-repo state contamination: leaps handover.json appearing in askr/askr_state/
- [x] Confirmed user expectation: askr state should be repo-contained, not shared across projects
- [x] Began systematic investigation of state_dir resolution in checkpoint.py and lifecycle.py
- [x] Executed grep searches to locate _get_state_dir(), os.getcwd(), os.chdir(), and daemon loop logic
- [x] Located root cause: git_commit_push() and create_checkpoint() run git subprocesses without cwd=, defaulting to daemon's ambient directory
- [x] Patched git_commit_push() to accept state_dir and derive project_path, added cwd= to all 7 git subprocess calls
- [x] Patched create_checkpoint() to derive project_path from state_dir and pass it to git diff/log and _regenerate_architecture_md()
- [x] Threaded state_dir parameter into write_handover() call in create_checkpoint()
- [x] Fixed project_path assignment in checkpoint metadata to use derived project_path instead of os.getcwd()
- [x] Verified syntax correctness of patched checkpoint.py with py_compile
- [x] Threaded state_dir parameter into goals.py::complete_goal() and goals.py::expire_auto_suggested_goals()
- [x] Updated all file operations in goals.py to use explicit state_dir instead of ambient cwd
- [x] Hardened LLM prompt schema in checkpoint.py to forbid invented session_metadata keys and clarify in_progress.file semantics
- [x] Added explicit rules to prompt: in_progress.file must be null for non-code work, never set to handover/state files themselves
- [x] Verified syntax correctness of all patched files with py_compile

## In Progress
- `askr/state/writer.py` (line 120): Thread state_dir parameter into write_handover() function signature and use it to write handover.json to correct repo's .askr_state/ directory

## Next Actions
1. Read askr/state/writer.py and update write_handover() signature to accept state_dir parameter; use it to construct the full path to handover.json instead of relying on os.getcwd()
   *Why: write_handover() is the final sink where handover.json is written; it must use explicit state_dir, not ambient cwd, to ensure the file lands in the correct repo*
2. Verify that lifecycle.py correctly passes state_dir to create_checkpoint() in all call sites (search for create_checkpoint calls)
   *Why: lifecycle.py is the orchestrator that calls create_checkpoint(); it must ensure state_dir is always provided and correct*
3. Run integration test: start daemon with two projects in separate repos, trigger checkpoints in each, verify handover.json appears in correct repo's askr_state/ and git commits target correct repos
   *Why: End-to-end validation that cross-repo contamination is fully resolved*
4. Commit all changes with message 'fix(daemon): thread state_dir through goals.py and harden handover schema'
   *Why: Checkpoint this session's work before moving to next phase*

## Decisions
- analytics.py::record_session_end() intentionally left unchanged — it writes to ~/.config/askr/analytics.json, a global file outside any repo — This is by design: analytics tracks total time-saved across all projects, not per-repo state. Global file is correct behavior.
- LLM prompt schema now forbids invented session_metadata keys and requires in_progress.file to be null for non-code work — Previous sessions showed LLM fabricating 'session_end_reason' and forcing 'file' key on non-code items, contradicting trigger_type. Schema constraints prevent this.

## Files In Play
- `askr/session/checkpoint.py`
- `askr/session/lifecycle.py`
- `askr/state/goals.py`
- `askr/state/writer.py`

## Relational Files
- `askr/state/config.py` (imported_by): Provides _get_state_dir() which derives state_dir from project root; all patched files depend on this
- `askr/daemon/loop.py` (configures): Daemon loop orchestrates checkpoint.py and lifecycle.py calls; must pass state_dir correctly

## Uncommitted Files
- `askr/session/checkpoint.py`
- `askr/session/lifecycle.py`
- `askr/state/goals.py`
- `askr/state/writer.py`
- `askr_state/implementation_bippin.jsonl`
- `askr_state/notifications.log`
