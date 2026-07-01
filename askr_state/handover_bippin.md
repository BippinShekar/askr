# Handover: bippin

Last updated: 2026-07-02 02:00

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions.

## Discussion
Session focused on voice notification preference schema design and initial implementation. Determined that voice_notifications is a machine-level user trait (stored in global ~/.config/askr/config.json) rather than per-project, mirroring the pattern of developer name. Added load_voice_enabled() and save_voice_enabled() helper functions to askr/state/config.py following existing config.py conventions. Architecture identified: voice notifications hook into existing notification infrastructure (askr/hooks/stop.py, notification.py) as an additional sink alongside Discord, requiring minimal mechanical changes to wire opt-in preference through init flow and state management.

## Accomplishments
- [x] LinkedIn location combobox field filling fixed with city name extraction and fallback retry pattern
- [x] Identified root cause of LinkedIn location field failures: full location strings do not trigger city autocomplete dropdown
- [x] Implemented two-part fix: prompt instructs extraction of city name from full location string, with retry on failure
- [x] Killed orphaned uvicorn process blocking backend logs
- [x] Conducted comprehensive security audit of apply agent code generation paths with four hardening fixes against prompt injection attacks
- [x] Fixed resume PDF portfolio URL lookup from qa_bank.portfolio_url to application_prefill.answers.portfolio_url
- [x] Updated PDF generator to render 'Portfolio' as link label instead of domain URL
- [x] Diagnosed Ramp application failure as Ashby spam_warning state (browser fingerprinting-based anti-bot detection)
- [x] Implemented spam_warning recovery with 'Learn more' probe to locate submit/submit-again button
- [x] Extended spam_warning handling to distinguish overlay banner (resubmit after scroll) vs form replacement (hard refresh required)
- [x] Refactored spam recovery strategy to defer spam-flagged jobs to end of session instead of inline retry
- [x] Investigated queue drain architecture and browser_stream replay buffer lifecycle
- [x] Scoped voice notification feature: confirmed macOS-only deployment enables native `say` TTS without cross-platform abstraction
- [x] Identified notification hook integration points (askr/hooks/stop.py, notification.py) for wiring voice updates as additional sink alongside Discord
- [x] Designed voice notification preference schema: machine-level boolean flag stored in global ~/.config/askr/config.json (not per-project)
- [x] Implemented load_voice_enabled() and save_voice_enabled() helper functions in askr/state/config.py following existing config pattern

## In Progress
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry
- `askr/state/config.py`: Voice notification system implementation: wire voice_enabled preference through askr init flow, integrate with existing notification hooks to announce task completion and session state transitions

## Next Actions
1. Implement voice preference prompt in askr init flow (mirror Discord webhook prompt pattern) to capture user opt-in during initialization
   *Why: Required before voice notifications can be triggered; determines UX for first-time setup and preference changes*
2. Create askr/hooks/voice.py notification sink that wraps macOS `say` command with error handling and optional volume/rate parameters
   *Why: Implements the actual TTS invocation; should follow notification.py Discord sink pattern for consistency*
3. Wire voice_enabled preference check into askr/hooks/stop.py and notification.py to conditionally invoke voice sink alongside Discord webhook
   *Why: Connects preference to actual notification dispatch; minimal mechanical change to existing hook infrastructure*
4. Add voice notification test coverage for load_voice_enabled/save_voice_enabled in tests/test_config.py
   *Why: Ensures preference persistence and retrieval work correctly; follows existing test patterns*

## Decisions
- Voice notification preference stored as machine-level boolean in global ~/.config/askr/config.json, not per-project — Voice is a user/machine trait (do I want this Mac to talk), not a per-project secret like discord_webhook; mirrors developer name pattern in config.py
- Voice notifications implemented as additional sink in existing notification infrastructure, not separate code path — Minimizes mechanical changes; reuses Discord webhook pattern (notification.py, hooks/stop.py) for consistency and maintainability
- macOS-only deployment using native `say` command without cross-platform abstraction — askr is macOS-only; native TTS avoids external dependencies and licensing complexity

## Files In Play
- `askr/state/config.py`

## Relational Files
- `askr/hooks/stop.py` (configures): Notification dispatch point where voice sink will be wired alongside Discord webhook
- `askr/hooks/notification.py` (configures): Existing notification sink pattern that voice implementation will mirror
- `askr/init.py` (configures): Init flow where voice preference prompt will be added (mirror Discord webhook prompt)
- `tests/test_config.py` (tested_by): Test coverage for load_voice_enabled/save_voice_enabled functions

## Uncommitted Files
- `askr/state/config.py`
- `askr_state/implementation_bippin.jsonl`
