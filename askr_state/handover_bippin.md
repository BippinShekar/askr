# Handover: bippin

Last updated: 2026-07-02 11:38

*Source of truth: `handover_bippin.json`*


## Task
Scoped a macOS voice notification feature (TTS via `say` command) into implementation stages, confirming prior session had already committed config scaffolding and identified integration points.

## Discussion
A prior session had begun building voice notification support by adding `load_voice_enabled()` and `save_voice_enabled()` to `askr/state/config.py` (commit f323a65). This session investigated the scope by grepping for voice/TTS references, confirmed macOS-only deployment (no cross-platform concern), and mapped the feature into a 3-stage rollout: (1) create `askr/clients/voice.py` with a `speak()` sink, (2) wire it into `askr/hooks/stop.py` and `notification.py`, (3) add init-time prompt to enable/disable. User requested staging breakdown for review before proceeding.

## Accomplishments
- [x] Confirmed prior session's config scaffolding (load_voice_enabled/save_voice_enabled in askr/state/config.py:31-38) is in place and committed
- [x] Mapped voice notification feature into 3-stage implementation plan with clear file targets and integration points
- [x] Verified macOS-only deployment is safe (no cross-platform TTS abstraction needed)

## In Progress
- `None`: Voice notification feature design — awaiting user review of 3-stage scope before implementation begins

## Next Actions
1. User to review and approve the 3-stage voice notification rollout plan (create voice.py client → wire into hooks → add init prompt)
   *Why: Session ended with user requesting scope review before proceeding; no implementation should start until approval*
2. Once approved, implement Stage 1: create askr/clients/voice.py with speak(text) function using subprocess.run(['say', text]), guarded by load_voice_enabled(), with silent failure if say unavailable
   *Why: Lowest-risk foundation; mirrors existing Discord client pattern*
3. Implement Stage 2: integrate speak() calls into askr/hooks/stop.py and askr/hooks/notification.py at task completion points
   *Why: Connects config to actual notifications; reuses existing hook infrastructure*
4. Implement Stage 3: add voice enable/disable prompt to cmd_init in askr/cli/askr.py (around line 740-750)
   *Why: Completes user-facing setup flow; matches existing init pattern*

## Decisions
- Voice notifications use macOS `say` command directly, not a cross-platform TTS abstraction — Project is macOS-only; `say` is built-in and reliable; no cross-platform users to support
- Voice client follows Discord client pattern: silent failure if `say` unavailable, guarded by load_voice_enabled() — Consistent error handling; non-blocking; matches existing notification sink design

## Files In Play
- `askr/state/config.py`
- `askr/hooks/stop.py`
- `askr/hooks/notification.py`
- `askr/cli/askr.py`

## Relational Files
- `askr/clients/discord.py` (imported_by): Voice client will follow same pattern (sink with error guard)
- `askr/state/config.py` (configures): Already holds load_voice_enabled/save_voice_enabled; voice.py will call these
- `askr/hooks/stop.py` (imports): Will import and call voice.speak() at task completion
- `askr/hooks/notification.py` (imports): Will import and call voice.speak() for notifications
