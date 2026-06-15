# Handover: bippin

Last updated: 2026-06-15 19:09

*Source of truth: `handover_bippin.json`*


## Task
Designed three-way decision tree for autonomous continuation after research-only sessions, distinguishing between research with implementation intent vs. research without actionable direction.

## Discussion
The previous session's logic treated all talk-only sessions as skip-worthy, losing valid research conclusions that end with 'let's implement X'. User raised the inverse case: research sessions that conclude without implementation intent. Session clarified the decision tree: coding sessions auto-continue with context; research+intent sessions surface a direction_proposal notification for user approval; research-only sessions (no implementation signal) should infer direction from the most recent prior coding session or surface a 'no direction' state. This requires a fourth signal type or refinement to Signal 3 logic to detect intent markers in session transcripts.

## Accomplishments
- [x] Identified gap in direction inference: research-only sessions need intent detection to decide between proposing direction vs. falling back to prior coding context
- [x] Clarified three-way notification routing: context (auto-continue), direction_proposal (user approval), and no-direction fallback (needs implementation)

## Next Actions
1. Add intent detection to `_infer_direction()` in lifecycle.py: scan session transcript for markers like 'let's implement', 'build', 'code', 'start', 'next step is' to classify research sessions as intent-bearing vs. intent-free.
   *Why: Research-only sessions without implementation intent should not trigger direction_proposal; instead they should fall back to the most recent coding session's direction or surface a 'no actionable direction' state.*
2. Extend Signal 3 return value to include `intent_detected: bool` alongside `proposed: bool`, allowing lifecycle to route research-only + no-intent to fallback logic instead of notification.
   *Why: Distinguishes between 'research concluded with next steps' (propose) and 'research concluded, no implementation signal' (fallback or idle).*
3. Update stop.py notification routing: if `proposed=True` and `intent_detected=False`, emit `no_direction` notification instead of `direction_proposal`, with message like 'Research session concluded. No implementation direction detected. Waiting for your input.'
   *Why: Prevents false-positive autonomous proposals when user is still in exploratory mode.*
4. Test end-to-end: create three test scenarios in test_lifecycle.py — (1) research + 'let's implement', (2) research + no intent, (3) research + fallback to prior coding — verify correct notification type and direction inference.
   *Why: Validates the three-way decision tree before autonomous sessions rely on it.*
5. Commit changes with message 'feat(lifecycle): intent detection for research-only sessions — distinguish propose vs. fallback'.
   *Why: Completes the direction inference logic and unblocks autonomous continuation for all session types.*

## Decisions
- Research-only sessions without implementation intent should NOT auto-propose direction; they should fall back to prior coding session or idle. — User may be in exploratory/research mode and not ready to commit to implementation. Auto-proposing wastes context and creates false-positive notifications.
- Intent detection should be transcript-based (keyword scanning) rather than user-provided metadata. — Avoids requiring explicit user tagging; intent markers are naturally present in session conclusions.

## Files In Play
- `askr/session/lifecycle.py`
- `askr/hooks/stop.py`
- `askr/ide/vscode-extension/extension.js`

## Relational Files
- `askr/session/handover.py` (imported_by): Handover history is walked by _infer_direction() to find prior coding sessions for fallback logic.
- `tests/test_lifecycle.py` (tested_by): Intent detection and three-way routing logic must be validated with test scenarios.

## Uncommitted Files
- `askr_state/notifications.log`

## Blockers
- Intent detection keywords not yet defined — need to finalize list of markers that signal implementation intent vs. exploratory research.
