# Handover: bippin

Last updated: 2026-06-12 19:01

# HANDOVER DOCUMENT

## Task
Investigate why autonomous session launched with stale "pricing and cost calculation" goal despite previous session marking it complete, and fix goal state management to prevent resurrection of finished work.

## Status
- `/Users/bippin/Desktop/askr/askr/clients/claude.py`: Fixed to prevent goal_part from overriding handover's Next Action with stale stored goal. Goal now passed as context, not directive.
- `/Users/bippin/Desktop/askr/askr/session/lifecycle.py`: Applied same fix — goal context separation.
- `/Users/bippin/Desktop/askr/askr/hooks/stop.py`: Applied same fix — goal context separation.
- `/Users/bippin/.cursor/extensions/askr.askr-status-1.0.0/extension.js`: Reduced prompt delay from 8s to 4s (original was 0s, 4s is safe minimum for Claude TUI initialization).
- `/Users/bippin/Desktop/askr/askr/ide/vscode-extension/extension.js`: Reduced prompt delay from 8s to 4s.
- Root cause identified: `_get_next_goal()` logic is resurrecting completed goals instead of respecting completion state in goals.md.

## Failed Approaches
- 8 second delay: Added as overly cautious, reverted to 4s (original code had 0s, 4s is proven safe).
- Storing goal as prompt_arg in session prompt: Rejected — causes new session to treat stale goal as active directive instead of reading fresh state from goals.md.

## Next Action
Read `/Users/bippin/Desktop/leaps/askr_state/goals.md` and examine `_get_next_goal()` implementation in the codebase to determine why completed goals are being returned as active. Trace the completion marking logic — verify that when a goal is marked done in goals.md, `_get_next_goal()` skips it and returns the next unfinished goal instead of cycling back to finished ones.

## Open Questions
- What is the exact completion marker format in goals.md that `_get_next_goal()` checks for?
- Is `_get_next_goal()` filtering by completion status at all, or is it returning goals in order without checking done/incomplete state?
