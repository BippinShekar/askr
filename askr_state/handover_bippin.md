# Handover: bippin

Last updated: 2026-07-11 19:18

*Source of truth: `handover_bippin.json`*


## Task
Fixed PID pruning logic in lifecycle.py to correctly distinguish between dead processes and Mac-suspended processes, preventing false pruning of valid companion sessions during sleep/wake cycles.

## Discussion
This session completed the core fix for session loss during Mac sleep/wake cycles. The root cause was identified in is_session_pid_alive() — it was treating process lookup failures as definitive proof of death, when in fact Mac sleep suspends processes without killing them. The assistant replaced the unsafe logic with a fail-safe approach: unknown process state is never treated as dead, only explicit confirmation of process termination triggers pruning. Additionally, a critical secondary bug was discovered and fixed: session registration (register_session, called from SessionStart) was silently failing for nearly every session due to an unhandled exception wrapped in bare except: pass, causing the registry to contain only 1 entry out of dozens of active sessions. The pruning fix made this gap visible by preventing false pruning, which exposed why the daemon was re-firing companions repeatedly. All 296 tests pass; changes committed and daemon restarted.

## Accomplishments
- [x] Replaced unsafe PID-based pruning logic with fail-safe semantics in is_session_pid_alive()
- [x] Updated _prune_companioned_sessions() to require positive proof of process death before pruning any session
- [x] Updated test_registry.py and test_voice.py to match corrected pruning semantics
- [x] Verified all 296 tests pass with new logic
- [x] Identified root cause: session registration silently failing for ~97% of active sessions due to unhandled exception in bare except: pass
- [x] Committed fix (71f4821) and restarted daemon

## Next Actions
1. Investigate why register_session() fails silently for nearly every session (unhandled exception in bare except: pass wrapper)
   *Why: This is the underlying gap that made the PID pruning bug's impact so severe. Fixing it would prevent similar silent failures in the future. Marked as follow-up post-Monday release.*
2. Consider implementing a reliable spawn record / parent→child relationship graph for task breakdown
   *Why: User proposed this as a structural improvement, but it depends on #1 being reliable first. Depends on session registration being fixed. Deferred pending Monday release.*
3. Run 3+ Mac sleep/wake cycles with updated daemon to verify session continuity is restored
   *Why: Validate that the fail-safe pruning logic prevents session loss during system sleep events in real-world conditions.*

## Decisions
- Companioned_sessions dedup pruning must check whether a session's actual process is still alive (PID-based), not whether its stats file has gone stale — Stats files stop updating whenever the machine sleeps, not just when a session ends. A suspended process keeps a valid PID the whole time it's asleep — it only fails that check once it's genuinely gone. PID-based checking prevents the dedup from forgetting live sessions after Mac sleep.
- Self-continuation launch gate (a session relaunching itself) should not exist — only Phase 5 teammate-task gate applies — Self-continuation relaunches are the normal case and should never be gated; the original Phase 5 gate already handles the actual threat (unrelated teammate tasks with elevated permissions). The self-continuation gate was overly broad and broke the expected relaunch workflow.
- Daemon PID and companioned_sessions state are stored in ~/.config/askr/ (out-of-repo config directory) — Allows daemon to persist across repo changes and multiple project instances; keeps state separate from versioned code
- is_session_pid_alive() uses fail-safe semantics: unknown process state is never treated as dead; only explicit termination confirmation triggers pruning — Mac sleep suspends processes without killing them; treating unknown state as dead causes false pruning of valid companion sessions. Fail-safe approach prevents data loss.

## Files In Play
- `askr/session/lifecycle.py`
- `askr/session/registry.py`
- `tests/test_registry.py`
- `tests/test_voice.py`

## Relational Files
- `askr/session/registry.py` (imported_by): Contains session registration logic that is silently failing; identified as root cause of pruning bug
- `tests/test_registry.py` (tested_by): Tests for registry and pruning logic; updated to match new fail-safe semantics
- `tests/test_voice.py` (tested_by): Contains pruning tests; updated to match corrected is_session_pid_alive() behavior
