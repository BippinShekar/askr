# Handover: bippin

Last updated: 2026-07-02 01:57

*Source of truth: `handover_bippin.json`*


## Task
Implemented macOS voice notification system for askr init to enable users to opt-in to spoken state updates via native `say` command, integrated with existing Discord notification hooks to announce task completion and session state transitions.

## Discussion
Session focused on adding voice notification capability to askr initialization flow. User requested voice updates during askr init to notify when Claude Code completes tasks and to warn about session limits, complementing existing Discord notifications. Investigation confirmed macOS-only deployment (safe to use native `say` TTS without cross-platform abstraction). Architecture identified: voice notifications should hook into existing notification infrastructure (askr/hooks/stop.py, notification.py) as an additional sink alongside Discord, requiring minimal mechanical changes to wire opt-in preference through init flow and state management.

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

## In Progress
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry
- `None`: Voice notification system implementation: wire opt-in preference through askr init flow, integrate with existing notification hooks to announce task completion and session state transitions

## Next Actions
1. Design voice notification preference schema for askr init (boolean flag in user config or session state)
   *Why: Required before implementation; determines where opt-in preference is stored and how it flows through session lifecycle*
2. Implement voice notification sink in notification.py or new module, wrapping native `say` command with task name and state transition messages
   *Why: Core implementation; should mirror Discord sink pattern to reuse existing hook infrastructure*
3. Wire voice preference into askr init CLI flow to prompt user for opt-in during initialization
   *Why: User-facing requirement; enables voice notifications to be enabled at setup time*
4. Test voice notifications for task completion ('done with <task>') and session state warnings (session limit approaching)
   *Why: Validates feature meets user requirements for state transition notifications*
5. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate (checkpoint.py create_checkpoint, trigger_type==emergency branch)
   *Why: Open goal from prior sessions; emergency handovers currently bypass proper LLM-based context generation*
6. Investigate guard_runner.py's non-blocking notification.json path (type: guard_warning) dead code and determine if Phase 3.5 IDE popup feature is still planned
   *Why: Open goal; code path never invoked from pre_tool_use.py or HOOK_MAP; clarify if feature should be removed or completed*

## Decisions
- Voice notifications use native macOS `say` command rather than cross-platform TTS library — Codebase is macOS-only deployment; native command is mechanically simpler and requires no additional dependencies
- Voice notifications integrate as additional sink in existing notification infrastructure (askr/hooks/stop.py, notification.py) rather than separate system — Minimizes mechanical changes; reuses existing hook patterns and state management for Discord notifications

## Files In Play
- `askr/hooks/stop.py`
- `askr/notification.py`
- `askr/cli/askr.py`

## Relational Files
- `askr/hooks/stop.py` (imports): Existing hook point where notification sinks are triggered; voice notifications will integrate here
- `askr/notification.py` (imports): Existing notification infrastructure; voice sink will be added alongside Discord sink
- `askr/cli/askr.py` (configures): Init flow where user voice preference will be prompted and stored
