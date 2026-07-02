# Handover: bippin

Last updated: 2026-07-02 13:55

*Source of truth: `handover_bippin.json`*


## Task
Implemented voice notification system with quota pre-warning, speak() sink gated by user preference, integration into stop/notification hooks, askr init prompt, comprehensive test coverage, confirmed guard_runner.py notification.json path is dead code, and added per-turn elapsed-time gating to suppress 'done' voice ping during active back-and-forth conversation.

## Discussion
The voice notification feature is complete across 6 stages with all commits pushed and tests passing. This session refined the 'done' notification UX by decoupling the Discord card gate from the voice speak() call and implementing per-turn elapsed-time gating: if the last user turn was < 10 seconds ago, the voice ping is suppressed to avoid interrupting active back-and-forth conversation. This addresses the user's earlier concern about passive-mode notification strategy. Session also added voice announcement for PreCompact emergency kill and humanized text inside speak() while keeping written copies untouched. All 25 voice tests pass; full test suite passes.

## Accomplishments
- [x] Added speak() sink function gated by voice_notifications preference
- [x] Wired speak() into stop.py notification hooks for task-done and HITL events
- [x] Added voice_notifications prompt to askr init flow
- [x] Implemented quota pre-warning at 75% threshold with quota_warned_sessions deduplication
- [x] Created test_voice.py with 25 tests covering speak() gating, config round-trip, quota-warning, and per-turn elapsed-time scenarios
- [x] All 6 voice notification stages committed and pushed to main
- [x] Confirmed guard_runner.py notification.json path is dead code (three independent sessions reached same conclusion)
- [x] Recorded guard_runner.py dead-code finding as formal decision to prevent re-investigation in future sessions
- [x] Decoupled Discord card gate from voice speak() call in stop.py
- [x] Implemented _turn_elapsed_seconds() helper to suppress 'done' voice ping if last user turn < 10 seconds ago
- [x] Added voice announcement for PreCompact emergency kill in pre_compact.py
- [x] Implemented humanize_for_speech() to convert written text to spoken form (e.g. 'Claude' → 'Claude', 'HITL' → 'human in the loop') while keeping written copies untouched

## In Progress
- `None`: User requested three new voice notification triggers with UX refinement: (1) task completion notification when Claude finishes and all hooks run — with strategy to avoid interrupting active back-and-forth conversation (passive-mode detection via per-turn elapsed time now implemented), (2) context-switch notification with clarification on whether askr init re-run is needed and whether voice_notifications preference persists across context switches, (3) message content for context-switch voice alert and where that event is triggered in codebase. User also requested voice_notifications be set to True globally in config rather than prompted per-session. Per-turn elapsed-time gating is now in place; context-switch notification and global config default remain open.

## Next Actions
1. Implement context-switch voice notification: identify where context switch is triggered in codebase (likely in session/checkpoint.py or hooks), add speak() call with humanized message (e.g. 'Switching context'), and test coverage
   *Why: User explicitly requested context-switch notification as one of three new triggers; this is the only major trigger not yet implemented*
2. Clarify and document whether voice_notifications preference persists across context switches or needs to be re-prompted; update askr init flow if needed
   *Why: User raised this as a clarification question; affects UX and config state management*
3. Change voice_notifications default from False to True in config schema (askr/state/config.py) and remove per-session prompt from askr init flow
   *Why: User requested voice_notifications be set globally in config rather than prompted per-session; reduces friction*
4. Decide on guard_runner.py dead-code path: delete notification.json writing code, wire up guard_runner.py to actually run, or document as dead code with rationale; escalate to user if no clear direction
   *Why: Three sessions have independently confirmed this path is dead code; prior deletion goal was discarded within 4 minutes with no rationale recorded; decision has been pending explicit user direction*

## Decisions
- Per-turn elapsed-time gating: suppress 'done' voice ping if last user turn was < 10 seconds ago — Addresses user's concern about voice notifications interrupting active back-and-forth conversation; implements passive-mode detection without requiring explicit mode tracking
- Humanize text inside speak() (e.g. 'HITL' → 'human in the loop') but keep written notification copies untouched — Voice output should be natural and conversational; written logs should remain precise and machine-readable
- Decouple Discord card gate from voice speak() call in stop.py — Allows independent control of voice notifications from Discord card visibility; enables per-turn elapsed-time gating without affecting card logic

## Files In Play
- `askr/hooks/stop.py`
- `askr/hooks/pre_compact.py`
- `askr/clients/voice.py`
- `tests/test_voice.py`
- `tests/test_context_cut_handover.py`

## Relational Files
- `askr/state/config.py` (configures): Stores voice_notifications preference; needs update to change default from False to True and remove per-session prompt
- `askr/session/checkpoint.py` (imported_by): Context switch logic likely resides here; needed to identify where to add context-switch voice notification
- `askr/hooks/pre_tool_use.py` (imported_by): Confirmed to run guard check synchronously in-process; guard_runner.py notification.json path is dead code
- `askr/hooks/guard_runner.py` (imported_by): Contains dead-code notification.json writing path (type: guard_warning); decision pending on delete, wire up, or document

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- User direction needed on guard_runner.py dead-code path: delete, wire up, or document with rationale
