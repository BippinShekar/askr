# Handover: bippin

Last updated: 2026-07-02 13:15

*Source of truth: `handover_bippin.json`*


## Task
Implemented voice notification feature end-to-end: added speak() sink gated by user preference, wired quota pre-warnings and task-done/HITL events to voice output, integrated voice prompt into askr init, and added comprehensive test coverage with quota-warning deduplication.

## Discussion
Prior sessions scoped voice notifications into 3 stages and built config scaffolding. This session completed Stage 4 (user-facing warnings) by implementing the full voice notification pipeline: speak() function using native macOS `say` command, integration with existing quota trigger (90%) and notification events (task-done, HITL), user preference prompt in init flow, and quota-warned session deduplication in stop.py to prevent duplicate warnings. All changes tested and committed.

## Accomplishments
- [x] Implemented speak() function in askr/clients/voice.py with macOS `say` command, guarded by load_voice_enabled() preference check, silent failure on unavailable command
- [x] Wired speak() to existing notification events: task-done (in stop.py:main()) and HITL prompts (in notification.py:notify_hitl_required())
- [x] Wired speak() to quota pre-warning trigger: fires at 90% quota threshold via existing QUOTA_TRIGGER infrastructure in lifecycle.py
- [x] Added voice_notifications boolean prompt to askr init flow (askr/cli/askr.py) with platform check for macOS
- [x] Implemented quota_warned_sessions deduplication in stop.py:main() mirroring companioned_sessions pattern to prevent duplicate quota warnings in same session
- [x] Created comprehensive test suite (tests/test_voice.py) covering speak() gating, config round-trip, quota-warning dedup, and notification event integration (11 tests, all passing)
- [x] Removed 14 repeated voice notification decision entries from askr_state/decisions.jsonl (kept original 3: macOS-only/say, additional-sink-not-separate-system, machine-level config storage)

## Next Actions
1. Commit askr_state/implementation_bippin.jsonl (session log) to complete this session's work
   *Why: Only uncommitted file remaining; all code changes already committed in 6 commits*
2. Verify voice feature end-to-end in live askr session: run askr init on fresh machine, confirm voice_notifications prompt appears, trigger quota warning at 90%, verify speak() output
   *Why: All unit tests pass but integration with real quota tracking and user interaction needs validation*
3. Document voice notification feature in README or FEATURES.md: list supported events (quota pre-warning, task-done, HITL), macOS-only requirement, preference storage location
   *Why: Feature is complete but undocumented for users; helps future maintainers understand scope*

## Decisions
- Voice notifications use native macOS `say` command directly, not a cross-platform TTS abstraction — Project is macOS-only; `say` is built-in and reliable; no cross-platform users to support
- Voice client follows Discord client pattern: silent failure if `say` unavailable, guarded by load_voice_enabled() — Consistent error handling; non-blocking; matches existing notification sink design
- Voice notification preference stored as machine-level boolean in global ~/.config/askr/config.json, not per-project — Voice is a user/machine trait (do I want this Mac to talk), not a per-project setting
- Voice feature reuses existing quota trigger (90% threshold) and notification events (task-done, HITL) rather than creating new quota tracking mechanism — Existing infrastructure already fires at correct thresholds; speak() is a new sink, not a new trigger; avoids duplication
- Quota-warned sessions tracked in lifecycle.py and cleared in stop.py:main() to deduplicate warnings within same session — Prevents user hearing same quota warning multiple times if multiple tools fire in same session; mirrors companioned_sessions pattern

## Files In Play
- `askr/clients/voice.py`
- `askr/hooks/notification.py`
- `askr/hooks/stop.py`
- `askr/cli/askr.py`
- `askr/session/lifecycle.py`
- `tests/test_voice.py`

## Relational Files
- `askr/session/lifecycle.py` (imports): Contains QUOTA_TRIGGER constant (90%) that voice feature reuses; quota_warned_sessions set managed here
- `askr/hooks/notification.py` (imported_by): notify_hitl_required() wired to speak() for HITL event notifications
- `askr/hooks/stop.py` (imported_by): main() wired to speak() for task-done event; quota_warned_sessions deduplication logic added here
- `askr/clients/discord.py` (configures): Voice client follows same pattern: load_voice_enabled() mirrors load_discord_enabled()
- `askr/session/monitor.py` (imports): Quota tracking happens here; lifecycle.py reads quota_pct to trigger warnings
- `tests/test_context_cut_handover.py` (tested_by): Provided test pattern for mocking lifecycle internals; test_voice.py follows same structure

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
