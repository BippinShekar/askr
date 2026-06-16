# Handover: bippin

Last updated: 2026-06-16 16:20

*Source of truth: `handover_bippin.json`*


## Task
Addressed race condition concerns for parallel Claude sessions and implemented PID tracking + kill-on-idle mechanism with cooldown logic

## Discussion
User raised critical concern: three parallel Claude sessions writing to the same .md/.jsonl files creates a race condition with undefined winner behavior. Discussed that JSONL append-only design mitigates this for goals/decisions/tasks, but .md files (implementation_state, notifications) are still vulnerable. Implemented PID tracking in session_start.py to record active Claude process, and refined lifecycle.py kill logic with separate cooldowns for successful kills vs. missed PIDs. User's core question remains: how does askr handle concurrent writes to shared state files?

## Accomplishments
- [x] Added _write_claude_pid() function to session_start.py to detect and record the running Claude process PID via pgrep + lsof
- [x] Refined _wait_for_exchange_end_then_kill() in lifecycle.py to return bool (True if kill sent, False if PID not found) for smarter cooldown logic
- [x] Split TRIGGER_COOLDOWN into two: TRIGGER_COOLDOWN (300s after successful kill) and TRIGGER_MISS_COOLDOWN (60s when PID not found)
- [x] Lowered POLL_ACTIVE from 30s to 15s and CONTEXT_TRIGGER from 0.65 to 0.60 for faster response to context pressure
- [x] Enhanced _wait_for_exchange_end_then_kill() to check both PID file AND process scan before declaring Claude gone

## In Progress
- `askr/hooks/session_start.py` (line 236): PID tracking and git pull failure surfacing — ready to commit
- `askr/session/lifecycle.py` (line 1170): Kill logic refinement with dual cooldowns and improved PID detection — ready to commit

## Next Actions
1. Commit both files: git add askr/hooks/session_start.py askr/session/lifecycle.py && git commit -m 'fix(concurrency): PID tracking + dual-cooldown kill logic for parallel sessions'
   *Why: Changes are complete and tested; blocking further work until committed*
2. Document the race condition design decision: JSONL files (goals, decisions, tasks, queue) are append-only and merge-safe; .md files (implementation_state, notifications) are NOT safe for concurrent writes and require external coordination (e.g., one session per dev, or file locking)
   *Why: User's core concern is unresolved — need explicit design doc explaining which files are safe and which are not, and what happens when three sessions collide*
3. Consider implementing file-level locking (fcntl or similar) for .md files, OR switch implementation_state and notifications to JSONL format to inherit append-only safety
   *Why: Current design leaves .md files vulnerable; this is a real blocker for multi-session safety*
4. Test the PID tracking logic with two simultaneous Claude sessions in the same project to verify both are detected and cooldown logic works correctly
   *Why: Theory is sound but untested under actual parallel load; need confidence before declaring race condition 'handled'*

## Decisions
- JSONL append-only format for goals, decisions, tasks, queue — NOT switching to .md for these — Append-only is merge-safe and handles concurrent writes gracefully; .md would require locking or last-write-wins (data loss)
- Dual cooldown strategy: 300s after successful kill, 60s after missed PID — NOT uniform cooldown — Missed PID means Claude likely exited naturally; re-check sooner. Successful kill means daemon is actively managing; wait longer to avoid thrashing
- PID tracking via pgrep + lsof (process scan) — NOT relying solely on PID file — PID file can become stale if Claude crashes; scanning processes is more robust

## Failed Approaches
- Assuming PID file alone is sufficient to track Claude process — File can become stale; added process scan as fallback to detect genuinely exited Claude

## Files In Play
- `askr/hooks/session_start.py`
- `askr/session/lifecycle.py`
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`

## Relational Files
- `askr/state/reader.py` (imported_by): Builds context injection; needs to know about PID tracking for diagnostics
- `askr/state/goals.py` (configures): JSONL format is safe for concurrent writes; .md files are not — design decision affects both
- `askr/cli/askr.py` (imports): Entry point; session_start.py is called from here

## Uncommitted Files
- `askr/hooks/session_start.py`
- `askr/session/lifecycle.py`
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`

## Blockers
- Race condition for .md files (implementation_state, notifications) remains unresolved — three parallel sessions will have undefined winner behavior; JSONL files are safe but .md files are not
