# Handover: bippin

Last updated: 2026-08-10 20:04

*Source of truth: `handover_bippin.json`*


## Task
Completed four-stage companion session handover pipeline and fixed stale-handover bugs in idle/goal-autolaunch and infer_direction paths, enabling seamless context carry-over and accurate trigger inference across autonomous session spawns.

## Discussion
Session 1 built the four-stage handover pipeline (liveness detection, scratch aggregation, response threading, compose-box capture) to enable seamless context carry-over when Claude Code spawns new sessions. This session identified and fixed two critical bugs in the same root cause: _start_claude() (idle/goal-autolaunch path) was the only launch path that never called _infer_direction() for ground-truth verification, and _infer_direction() itself had a staleness gap — it trusted the newest handover with non-empty next_actions without checking for commits landed since that handover was written. A session can finish real work, commit it, and end without crossing a trigger threshold, leaving canonical handover stale. Both fixes are now live (commit 47cd3c6), and all 544 tests pass. The overnight autonomous orchestrator test from Session 1 remains the critical next validation step.

## Accomplishments
- [x] Identified root cause of token-wasting bug: _start_claude() never called _infer_direction(), and _infer_direction() had zero staleness cross-check against commits since handover was written
- [x] Wired _start_claude() (idle/goal-autolaunch and post-quota-reset relaunch path) through _infer_direction() for ground-truth trigger verification, matching behavior of _open_companion_session and stop.py relaunch paths
- [x] Added staleness cross-check to _infer_direction(): now verifies no real (non-askr) commits exist between candidate handover and HEAD before returning stale next_actions; falls through to Signal 4 (commit-momentum) if commits found
- [x] Added 2 new unit tests to test_infer_direction_signal_quality.py covering _start_claude() wiring and staleness cross-check logic; all 9 tests in file pass
- [x] Verified full test suite: 544/544 tests pass across all test files
- [x] Committed fix with clean git history (commit 47cd3c6) and comprehensive commit message explaining root cause, impact, and both fixes
- [x] Pushed stale-handover fix to origin/main

## Next Actions
1. Run overnight autonomous orchestrator test: plug into power, run caffeinate, seed goals.jsonl with at least one goal, confirm daemon is running via launchd (askr launch), then let it run unattended overnight
   *Why: Critical validation that the four-stage handover pipeline and stale-handover fixes work end-to-end in autonomous mode; will reveal any remaining context/quota/session-tree issues before declaring the feature production-ready*
2. After overnight run completes, query the structured event log (askr/state/events.jsonl) to build visualization dashboard showing session tree, context/quota savings across sessions, trigger type distribution, and multi-session persistence story
   *Why: Provides empirical evidence of handover effectiveness and identifies any patterns of wasted context or repeated work across session boundaries*
3. Monitor compose-box capture for false positives or missed carries during the overnight run; if the parser misses valid input or captures noise, refine extractPendingInput() logic in extension.js and re-test against the six realistic cases
   *Why: Ensures unsent terminal input is reliably carried over without noise, completing the user-experience continuity of the handover pipeline*
4. If overnight run succeeds, document the four-stage companion handover feature in CLAUDE.md and add it to the project README as a core capability of the autonomous orchestrator
   *Why: Makes the feature discoverable and maintainable for future developers; establishes it as a stable, documented part of the system*
5. Do NOT build auto-typing at the 5-hour hard limit without: (1) exact confirmation of what Claude Code's CLI shows when the account hits the real limit (passive message vs. interactive prompt), and (2) a design decision on whether auto-type happens unconditionally at reset time or only if terminal has been untouched since limit hit
   *Why: Current terminal-targeting mechanism (VS Code extension createTerminal) does not reach Cursor's integrated terminal panel; AppleScript fallback cannot reach WebView panes. Auto-typing into a terminal the user is actively reading is more invasive than any notification built so far and requires explicit user intent, not silent defaults.*

## Decisions
- Exempt read-only Bash commands (cat, ls, tail, grep) from cross-repo block guard while maintaining write/edit security — Allows safe inspection of files across repos without compromising guard integrity for write operations
- Replace raw regex split with shlex tokenization for Bash command parsing — Honors quoted strings and complex patterns in command arguments, preventing false positives in guard logic
- Skip status:fixed entries from task-held notification count as defensive fix — Independent of per-task discard API, reduces noise in held-task notices
- Split quota notification into three independent phases (silent poll → user notification → reset wait) instead of a single blocking check — Users working quickly were being interrupted at 90% threshold instead of real quota edge; silent polling lets them work to the genuine limit before notification
- Implement best-effort parent_session_id linking by observing launch_mode.json on first session_id sighting — Enables session tree reconstruction from event log without requiring explicit parent-passing through all spawn sites; gracefully handles sessions that don't have a parent (root sessions)
- Make append_event() fail open (non-fatal) to match codebase convention for non-critical writes — Event logging failures should not crash trigger evaluation; aligns with existing pattern for optional instrumentation
- Wire _start_claude() through _infer_direction() for ground-truth trigger verification, matching _open_companion_session and stop.py relaunch paths — Prevents idle/goal-autolaunch from blindly executing stale next_actions without verifying they are still valid; closes the only launch path that skipped verification entirely
- Add staleness cross-check to _infer_direction(): verify no real commits exist between candidate handover and HEAD before returning stale next_actions — Prevents sessions that finish work and commit without crossing a trigger threshold from leaving canonical handover stale; ensures fresh autonomous launches do not re-verify already-resolved issues

## User-Rejected Approaches
- **Build auto-typing into the terminal at the 5-hour hard limit to automatically resume Claude Code sessions** — "Do not infringe on the user's control; auto-typing into a terminal the user might be mid-thought in front of is more invasive than any notification built so far" (domain: askr/ide/vscode-extension/extension.js, terminal automation)

## Files In Play
- `askr/session/lifecycle.py`
- `askr/session/checkpoint.py`
- `askr/hooks/session_start.py`
- `askr/ide/vscode-extension/extension.js`
- `tests/test_infer_direction_signal_quality.py`
- `tests/test_quota_notify_split.py`
- `tests/test_context_cut_handover.py`
- `tests/test_git_push_honesty.py`
- `tests/test_blockers.py`

## Relational Files
- `askr/session/infer_direction.py` (imported_by): Core trigger inference logic that now receives calls from _start_claude() and includes staleness cross-check
- `askr/session/stop.py` (imported_by): Relaunch path that already called _infer_direction(); now consistent with _start_claude() behavior
- `askr/state/events.jsonl` (configures): Structured event log that will be queried after overnight test to validate session tree and handover effectiveness
