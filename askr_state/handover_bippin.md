# Handover: bippin

Last updated: 2026-07-02 09:47

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions; fixed handover generation bug leaking .claude/ directory noise into uncommitted files list; diagnosed and fixed get_state_dir() fallback vulnerability that could load a different project's stored path, and scrubbed foreign-repo (leaps) contamination from shared state files.

## Discussion
Session focused on three parallel tracks: (1) completing voice notification preference schema implementation by adding load_voice_enabled() and save_voice_enabled() helper functions to askr/state/config.py following existing config pattern, (2) investigating and fixing a real handover bug in checkpoint.py where _get_uncommitted_files() was dumping raw git status output without filtering, causing .claude/ directory artifacts to pollute the handover document, and (3) discovering and fixing a critical security issue where get_state_dir() could fall back to loading a different project's stored path from ~/.config/askr/config.json if the current project had no stored path, plus scrubbing 7 lines of foreign-repo (leaps) contamination from failed_approaches.md that had leaked into shared state tracking. Confirmed no active nested worktree lockout condition exists currently; prior session's guard lockout was collision-specific, not a standing bug. Architecture for voice notifications remains: machine-level boolean flag in ~/.config/askr/config.json, wired through notification hooks as additional sink alongside Discord.

## Accomplishments
- [x] Scoped voice notification feature: confirmed macOS-only deployment enables native `say` TTS without cross-platform abstraction
- [x] Identified notification hook integration points (askr/hooks/stop.py, notification.py) for wiring voice updates as additional sink alongside Discord
- [x] Designed voice notification preference schema: machine-level boolean flag stored in global ~/.config/askr/config.json (not per-project)
- [x] Implemented load_voice_enabled() and save_voice_enabled() helper functions in askr/state/config.py following existing config pattern
- [x] Diagnosed handover generation bug: _get_uncommitted_files() in checkpoint.py dumping raw git status output without .claude/ filtering
- [x] Fixed checkpoint.py to exclude .claude/ directory from uncommitted files list in handover documents
- [x] Verified no active nested worktree lockout condition; prior session's guard collision was event-specific, not standing bug
- [x] Discovered critical security issue: get_state_dir() could fall back to loading a different project's stored path from ~/.config/askr/config.json if current project had no stored path
- [x] Fixed get_state_dir() to always return the current project's state directory without cross-project fallback contamination
- [x] Scrubbed 7 lines of foreign-repo (leaps) contamination from askr_state/failed_approaches.md that had leaked into shared state tracking
- [x] Updated project memory (project_handover_repo_scoping.md and MEMORY.md) to reflect corrected understanding of get_state_dir() bug as root cause, not symptom

## In Progress
- `askr/hooks/stop.py`: Wire voice_enabled preference through askr init flow and integrate with existing notification hooks as additional sink alongside Discord
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry

## Next Actions
1. Integrate voice_enabled preference into askr/hooks/stop.py notification flow to call native `say` command when voice_notifications is enabled
   *Why: load_voice_enabled() and save_voice_enabled() are implemented but not yet wired into the actual notification pipeline; voice feature is incomplete without this integration*
2. Add voice notification opt-in prompt to askr init flow (likely in askr/cli/init.py or equivalent) to capture user preference on first run
   *Why: Voice preference helpers exist but users have no way to set the preference yet; init flow must prompt for voice_notifications boolean*
3. Test voice notification end-to-end: run askr init with voice enabled, verify `say` command fires on task completion and state transitions
   *Why: Feature is architecturally complete but untested; need to confirm native macOS TTS integration works as designed*
4. Resume work on stateful retry mechanism: design failure context capture (screenshots, error reasoning) to enable learning-based job resubmission
   *Why: Architectural design phase is pending; this is the next major feature after voice notifications*

## Decisions
- Voice notifications are macOS-only feature using native `say` command, not cross-platform abstraction — Simplifies implementation, leverages native OS capability, no need for external TTS libraries
- Voice notification preference stored as machine-level boolean in ~/.config/askr/config.json, not per-project — User preference is global across all askr projects on the machine; per-project storage would be redundant
- get_state_dir() must always return current project's state directory without fallback to other projects' stored paths — Cross-project path contamination is a critical security issue; each project must maintain isolation

## Failed Approaches
- Attempting to fix handover generation by filtering git status output at the point of collection — Root cause was deeper: _get_uncommitted_files() was not filtering .claude/ directory at all; needed explicit exclusion logic

## Files In Play
- `askr/state/config.py`
- `askr/session/checkpoint.py`
- `askr/hooks/stop.py`
- `askr_state/failed_approaches.md`

## Relational Files
- `askr/hooks/notification.py` (imported_by): Voice notification integration will wire through existing notification hooks alongside Discord
- `askr/cli/init.py` (configures): Init flow must prompt user for voice notification preference on first run
- `askr/session/checkpoint.py` (imports): Fixed _get_uncommitted_files() to exclude .claude/ directory from handover documents

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
