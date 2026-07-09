# Handover: bippin

Last updated: 2026-07-09 13:59

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented a Phase 5 approval gate for autonomous session relaunch (quota-trigger, context-trigger, goal-autolaunch) that holds dangerous sessions pending explicit approval, added IDE popup handlers for task_approval_pending and guard_warning notifications, and fixed critical transcript-truncation bugs, race conditions in lifecycle triggers, false-positive idle-trigger fires, phantom-session warnings, and cross-process voice serialization.

## Discussion
This session completed the Phase 5 approval gate by wiring _launch_gate_check() into _start_claude() (quota/goal paths) and _open_companion_session() (context path), holding dangerous sessions' autonomous relaunches pending `askr launch approve`. The gate mirrors the existing task-approval model but covers the session's own continuation rather than queued teammate work. Simultaneously, the IDE extension's checkNotification() was updated to render task_approval_pending and guard_warning as purpose-built popups with Approve/Discard buttons, closing the gap where these notifications were falling through to generic fallback handling. All 188 tests pass; git history confirms two feature commits (lifecycle gate + IDE handlers) plus checkpoint entries. The roadmap was updated to reflect Phase 5 completion and the new dangerous_autolaunch_pending notification type.

## Accomplishments
- [x] Implemented Phase 5 approval gate for autonomous session relaunch: _launch_gate_check() wired into _start_claude() (quota-trigger, goal-autolaunch) and _open_companion_session() (context-trigger); dangerous sessions held pending `askr launch approve`; checkpointing still happens either way, only new-terminal spawn is held
- [x] Added IDE popup handlers in extension.js checkNotification(): task_approval_pending renders warning with Approve/Discard buttons, guard_warning renders informational popup, dangerous_autolaunch_pending renders Approve button; all run appropriate CLI commands in new terminal
- [x] Updated roadmap.md to reflect Phase 5 completion and document dangerous_autolaunch_pending notification type as part of the new launch gate
- [x] Verified all 188 tests passing after lifecycle and IDE changes; no regressions introduced

## Next Actions
1. Commit final implementation_bippin.jsonl checkpoint entry and push to main
   *Why: Session work is complete and tested; final checkpoint entry documents the launch gate and IDE handler implementation*
2. Restart daemon with `askr launch --restart` and verify approval gate flow under normal operation: trigger a quota/context/goal relaunch on a dangerous session and confirm it holds pending approval
   *Why: New gate logic needs validation in live environment to confirm approval flow works end-to-end and no regressions in checkpoint/notification timing*
3. Test IDE popup rendering: verify task_approval_pending, guard_warning, and dangerous_autolaunch_pending notifications display correctly in VS Code and button actions execute expected CLI commands
   *Why: IDE handlers are new code paths; visual rendering and button action execution must be validated in the actual extension environment*

## Decisions
- Both quota-trigger and context-trigger wait for Stop-hook signal before checkpointing or launching companion sessions — Eliminates race conditions where checkpoint could capture half-finished turns; authoritative turn-completion signal is the only safe synchronization point for trigger actions
- Idle trigger is suppressed while a turn is actively in progress via _turn_currently_active() gate; turn-start markers are written by user_prompt_submit.py and compared against most recent turn-stop marker — _last_turn_stop() only measures elapsed time since the PREVIOUS turn's Stop event and has no knowledge of whether a new turn has started; idle_secs would grow through an entire in-progress turn, firing false positives during normal thinking gaps. Turn-start markers provide authoritative signal of active user interaction.
- Abandoned turn-start markers (older than MAX_TURN_ACTIVE_SECS = 30 min with no matching stop) are treated as inactive rather than permanently blocking idle-checkpoint — Crashed or closed sessions should not permanently disable the idle-checkpoint safety net; 30 minutes is a reasonable upper bound for a single turn's processing time
- Companion-session handover only claims a previous session is still running when a live process is actually found; otherwise directs new session to pick up from Next Action directly — Unconditionally warning about phantom sessions that don't exist leaves new sessions deferring to non-existent work; the claim must be grounded in actual process detection
- All voice output across independent processes (daemon trigger thread, per-turn background handover async pings, hook processes) is serialized via cross-process flock to prevent concurrent `say` invocations from overlapping — Multiple independent OS processes call speak()/speak_signature() with no coordination; concurrent invocations play on top of each other and audibly garble into nonsense. A shared lock file ensures only one process speaks at a time, and speak_signature's prefix+body pair is locked as one atomic unit to prevent interleaving.
- Autonomous session relaunch (quota-trigger, context-trigger, goal-autolaunch) is gated on dangerous session permissions: when triggering session has --dangerously-skip-permissions or equivalent unrestricted Bash/rm access, relaunch is held pending explicit `askr launch approve` — Companion sessions inherit the exact same zero-friction permission state from their triggering session; without a gate, a dangerous session's autonomous relaunch would bypass approval entirely. Checkpointing still happens either way; only the new-terminal spawn is held, mirroring the task-approval model.
- IDE notifications task_approval_pending and guard_warning are rendered as purpose-built popups with context-specific actions (Approve/Discard buttons for task_approval_pending, informational-only for guard_warning) rather than generic fallback messages — Generic fallback handling left users with no way to act on these notifications; purpose-built cases provide clear action paths and match the non-blocking design intent in roadmap Phase 3.5

## User-Rejected Approaches
- **Manual post-generation truncation of LLM outputs to fit context windows** — "Rejected; requires instead that token limits be enforced via max_tokens parameter on API calls" (domain: clients/claude.py, checkpoint.py)

## Failed Approaches
- [2026-07-02] Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire — Semantic confusion between user-initiated turns and system-generated responses; required adding explicit turn-start markers to distinguish active user interaction from background processing
- [2026-07-04] Debouncing continuous per-turn checkpoints to reduce frequency while keeping the hook active — User rejected the entire continuous-checkpoint model; the problem is not frequency but the fundamental design of checkpointing on every turn, which blocks user interaction — User rejected the underlying model; frequency reduction does not address the core architectural issue
- [2026-07-04] Reusing `_execute_trigger()` for all three trigger types (quota, context, idle) — Idle conditions have different semantics than quota/context emergencies; code-path reuse caused misannouncement and unwanted session auto-launch — Idle trigger has fundamentally different semantics (background safety net vs. emergency response); shared code path caused incorrect behavior and false announcements
- [2026-07-06] Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds() — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire — Duplicate of 2026-07-02 failure; semantic confusion persisted until turn-start markers were added
- [2026-07-06] Reusing _execute_trigger() for all three trigger types (quota, context, idle) — Idle conditions have different semantics than quota/context emergencies; code-path reuse caused misannouncement and unwanted session auto-launch — Duplicate of 2026-07-04 failure; architectural separation required

## Files In Play
- `askr/session/lifecycle.py`
- `askr/cli/askr.py`
- `askr/ide/vscode-extension/extension.js`
- `roadmap.md`

## Relational Files
- `askr/session/checkpoint.py` (configures): Roadmap documents implementation status of checkpoint.py features (transcript truncation fixes, plan tool-call preservation, handover LLM input integrity)
- `askr/session/lifecycle.py` (configures): Roadmap documents implementation status of lifecycle.py trigger semantics (quota/context/idle trigger synchronization, turn-start markers, phantom-session detection, launch gate for dangerous sessions)
- `askr/clients/voice.py` (configures): Roadmap documents implementation status of voice.py cross-process serialization for speak() and speak_signature()
- `askr_state/decisions.jsonl` (imported_by): Roadmap references decisions.jsonl auto-population (Phase 3.17); this session added decision entries documenting launch gate and IDE handler architectural choices
- `tests/test_launch_gate.py` (tested_by): New test file validating _launch_gate_check() behavior across quota-trigger, context-trigger, and goal-autolaunch paths; all 6 tests passing

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
