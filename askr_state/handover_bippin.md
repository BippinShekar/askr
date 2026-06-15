# Handover: bippin

Last updated: 2026-06-15 17:42

*Source of truth: `handover_bippin.json`*


## Task
Redesigned _infer_direction() to use semantic commit-scope analysis instead of root-folder momentum, eliminating false-positive signals that cleared the gate at low confidence

## Discussion
Identified that Signal 3 (top-level directory frequency) was a design flaw — every commit in any repo touches some top-level folder, making it noise at 0.72 confidence that incorrectly passed the gate. Replaced it with semantic file-change analysis using conventional commit scopes (feat(scope), fix(scope)) parsed from git log. Tested all three signals in isolation: Signal 1 (dirty files) fires at 0.95, Signal 3 (handover next_actions) at 0.85, and the new semantic scope signal correctly identifies lifecycle as the active domain with 0.65 confidence from recent commit history.

## Accomplishments
- [x] Rewrote _infer_direction() Signal 3 to parse conventional commit scopes instead of root-folder frequency
- [x] Fixed scope regex to correctly extract scope from commit message (removed incorrect ^ anchor)
- [x] Validated all three direction signals in isolation with test harness
- [x] Committed lifecycle.py changes to main branch

## Next Actions
1. Run full end-to-end test of _infer_direction() with a fresh session start to verify the three-signal chain produces correct direction inference without HITL gate
   *Why: Signals are individually validated but full chain integration needs confirmation before rolling out to production sessions*
2. Stress-test _infer_direction() against edge cases: empty git log, no conventional commits, all commits in same scope, dirty files in multiple domains
   *Why: Robustness required before autonomous sessions rely on this for direction inference*
3. Update handover prompt in _generate_handover_prompt() to document the three-signal model and confidence thresholds (0.95 for dirty, 0.85 for handover, 0.65 for semantic scope)
   *Why: Next session needs to understand how direction was inferred and why confidence levels matter*
4. Verify HITL gate behavior: confirm that direction_confirm is triggered only when max(signal_confidences) < 0.70, and that it correctly surfaces the three competing signals to the user
   *Why: Gate is the safety mechanism preventing low-confidence direction from silently steering the session*

## Decisions
- Replaced top-level directory frequency (Signal 3) with semantic commit-scope analysis — Directory frequency is noise in any repo — every commit touches some top-level folder. Conventional commit scopes (feat(scope), fix(scope)) provide semantic signal about which domain was active in recent work
- Kept Signal 1 (dirty files) and Signal 2 (handover next_actions) unchanged — Both are high-fidelity: dirty files are immediate context, and handover next_actions are explicit developer intent from the previous session

## Failed Approaches
- Using regex with ^ anchor to match commit scope in git log output — ^ anchors to start of line, but commit message comes after the hash. Removed anchor to match scope anywhere in the message

## Files In Play
- `askr/session/lifecycle.py`

## Relational Files
- `askr_state/handover_bippin.json` (imported_by): Signal 2 reads next_actions[0] from this file to infer direction from explicit developer intent
- `askr/session/stop.py` (imports): _infer_direction() is called by stop.py to populate the direction_confirm gate

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
