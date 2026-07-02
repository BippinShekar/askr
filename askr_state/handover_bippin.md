# Handover: bippin

Last updated: 2026-07-02 13:16

*Source of truth: `handover_bippin.json`*


## Task
Implemented voice notification system with quota pre-warning, speak() sink gated by user preference, integration into stop/notification hooks, askr init prompt, and comprehensive test coverage.

## Discussion
The voice notification feature is now complete across 5 stages: a speak() sink that respects voice_notifications config preference, wiring into task-done and HITL notification events via stop.py hooks, user onboarding prompt in askr init, quota pre-warning at 75% threshold with deduplication via quota_warned_sessions, and 11 new tests covering gating, config round-trip, and quota-warning behavior. All commits are pushed and tests pass.

## Accomplishments
- [x] Added speak() sink function gated by voice_notifications preference
- [x] Wired speak() into stop.py notification hooks for task-done and HITL events
- [x] Added voice_notifications prompt to askr init flow
- [x] Implemented quota pre-warning at 75% threshold with quota_warned_sessions deduplication
- [x] Created test_voice.py with 11 tests covering speak() gating, config round-trip, and quota-warning scenarios
- [x] All 5 stages committed and pushed to main

## Next Actions
1. Investigate guard_runner.py's non-blocking notification.json path (type: guard_warning) — verify if it is truly dead code or if pre_tool_use.py HOOK_MAP needs updating to invoke it
   *Why: Open goal notes this path is never invoked from pre_tool_use.py, HOOK_MAP, or .claude/settings.json; Phase 3.5's IDE popup for non-blocking guard warnings cannot fire today regardless of extension.js whitelist fix*
2. Review and test the full voice notification flow end-to-end in a real session to confirm speak() is called at correct times and respects user preference
   *Why: Unit tests pass but integration with actual task lifecycle and notification events should be validated*

## Decisions
- Voice notifications are gated by voice_notifications boolean preference stored in config — Allows users to opt-in/out of audio feedback without code changes
- Quota pre-warning fires at 75% threshold and deduplicates via quota_warned_sessions set in lifecycle state — Prevents spam of repeated warnings while giving user early notice before hitting hard limit
- speak() is a sink function that logs and returns early if voice_notifications is False — Simplifies call sites — no conditional logic needed before calling speak()

## Files In Play
- `askr/session/lifecycle.py`
- `askr/hooks/stop.py`
- `tests/test_voice.py`

## Relational Files
- `askr/session/lifecycle.py` (imports): Defines quota_warned_sessions state and lifecycle management for voice notifications
- `askr/hooks/stop.py` (imports): Integrates speak() calls into task-done and HITL notification event hooks
- `askr/cli/init.py` (configures): Prompts user for voice_notifications preference during askr init
- `tests/test_context_cut_handover.py` (tested_by): Provided test pattern and mocking approach for lifecycle internals used in test_voice.py

## Blockers
- guard_runner.py non-blocking notification.json path (type: guard_warning) is dead code — unclear if this is intentional or requires HOOK_MAP fix
