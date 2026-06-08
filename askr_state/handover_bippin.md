# Handover: bippin

Last updated: 2026-06-08 19:32

## Task
Fix multi-repo context-switch daemon bug where the daemon fires a session handover in the wrong repository when multiple askr projects are active simultaneously.

## Status
- Root cause identified: `session_stats.json` is a single global file that gets overwritten by whichever repo's `PostToolUse` runs last. When repo B overwrites stats with its `project_path`, the daemon fires for repo B while user is actively working in repo A.
- Solution implemented in `/Users/bippin/Desktop/askr/askr/session/lifecycle.py`: added stale-stats check before firing trigger. The daemon now calls `_find_active_jsonl(project_path)` to locate the JSONL for the current project, checks its mtime, and skips the trigger if the JSONL hasn't been touched in 3+ minutes (indicating stats are stale from a different repo).
- `_find_active_jsonl` function confirmed to exist in monitor.py and returns the most recently modified JSONL in a project's sessions directory.
- Fix verified to be in place and ready for testing.

## Failed Approaches
- None documented in final state.

## Next Action
Test the multi-repo scenario: run askr in two separate project directories simultaneously, trigger context accumulation in one repo, and verify the daemon does NOT fire a hand
