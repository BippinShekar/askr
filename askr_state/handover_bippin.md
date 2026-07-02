# Handover: bippin

Last updated: 2026-07-02 09:41

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions; fixed handover generation bug leaking .claude/ directory noise into uncommitted files list.

## Discussion
Session focused on two parallel tracks: (1) completing voice notification preference schema implementation by adding load_voice_enabled() and save_voice_enabled() helper functions to askr/state/config.py following existing config pattern, and (2) investigating and fixing a real handover bug in checkpoint.py where _get_uncommitted_files() was dumping raw git status output without filtering, causing .claude/ directory artifacts to pollute the handover document. Confirmed no active nested worktree lockout condition exists currently; prior session's guard lockout was collision-specific, not a standing bug. Architecture for voice notifications remains: machine-level boolean flag in ~/.config/askr/config.json, wired through notification hooks as additional sink alongside Discord.

## Accomplishments
- [x] Scoped voice notification feature: confirmed macOS-only deployment enables native `say` TTS without cross-platform abstraction
- [x] Identified notification hook integration points (askr/hooks/stop.py, notification.py) for wiring voice updates as additional sink alongside Discord
- [x] Designed voice notification preference schema: machine-level boolean flag stored in global ~/.config/askr/config.json (not per-project)
- [x] Implemented load_voice_enabled() and save_voice_enabled() helper functions in askr/state/config.py following existing config pattern
- [x] Diagnosed handover generation bug: _get_uncommitted_files() in checkpoint.py dumping raw git status output without .claude/ filtering
- [x] Fixed checkpoint.py to exclude .claude/ directory from uncommitted files list in handover documents
- [x] Verified no active nested worktree lockout condition; prior session's guard collision was event-specific, not standing bug

## In Progress
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry
- `askr/hooks/stop.py`: Wire voice_enabled preference through askr init flow and integrate with existing notification hooks as additional sink alongside Discord

## Next Actions
1. Integrate voice_enabled preference into askr/hooks/stop.py notification flow to call native `say` command when voice_notifications is enabled
   *Why: load_voice_enabled() and save_voice_enabled() are implemented but not yet wired into the actual notification pipeline; voice feature is incomplete without this integration*
2. Add voice notification opt-in prompt to askr init flow (likely in askr/cli/init.py or equivalent) to capture user preference on first run
   *Why: Voice preference helpers exist but users have no way to set the preference yet; init flow must prompt for voice_notifications boolean*
3. Test voice notification end-to-end: run askr init with voice enabled, verify `say` command fires on task completion and state transitions
   *Why: Feature is architecturally complete but untested; need to confirm native macOS TTS integration works as designed*
4. Resume work on stateful retry mechanism design: define failure context schema (screenshots, error reasoning, job metadata) for learning-based resubmission
   *Why: Architectural design is in-progress; this is the next major feature after voice notifications and will improve job success rates*

## Decisions
- Voice notifications are machine-level user trait, not per-project — Mirrors existing pattern of developer name; users want consistent voice preference across all projects on a machine
- Voice notifications are macOS-only feature using native `say` command — Avoids cross-platform TTS abstraction complexity; native command is reliable and requires no external dependencies
- Voice notifications hook into existing notification infrastructure as additional sink alongside Discord — Minimal mechanical changes required; reuses established notification dispatch pattern in stop.py and notification.py
- Handover uncommitted files list must exclude .claude/ directory — Claude session artifacts (.claude/) are internal tooling noise and pollute handover documents; they should never appear in project state

## Failed Approaches
- Dumping raw git status --short --porcelain output directly into handover uncommitted files list — Includes .claude/ directory artifacts and other internal tooling noise that pollutes handover documents and confuses future sessions

## Files In Play
- `askr/state/config.py`
- `askr/session/checkpoint.py`

## Relational Files
- `askr/hooks/stop.py` (imports|configures): Will integrate voice_enabled preference into notification pipeline; currently imports notification.py
- `askr/hooks/notification.py` (configures): Existing notification dispatch sink; voice notifications will be added as additional sink alongside Discord
- `askr/cli/init.py` (configures): Will add voice notification opt-in prompt to askr init flow to capture user preference on first run
- `tests/test_config.py` (tested_by): Should add test coverage for load_voice_enabled() and save_voice_enabled() helper functions

## Uncommitted Files
- `askr/state/config.py`
- `askr_state/implementation_bippin.jsonl`
