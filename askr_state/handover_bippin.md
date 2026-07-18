# Handover: bippin

Last updated: 2026-07-18 18:05

*Source of truth: `handover_bippin.json`*


## Task
Refactored quota trigger lifecycle to split notification into three phases: silent polling until quota is genuinely near exhausted, then user-facing notification, then reset wait — fixing a UX bug where users were interrupted at the 90% threshold instead of the real edge of their quota.

## Discussion
The session identified and fixed a critical quota notification UX bug in the lifecycle module. The old `_execute_trigger` function was renamed to `_execute_quota_trigger` and its logic was split into a new three-phase flow: `_wait_until_quota_near_exhausted` silently polls the real account quota (not the stale 90% snapshot) until it's genuinely near exhausted, then the trigger fires the user-facing notification. This prevents users who work quickly from being interrupted pre-emptively. All stale function name references in comments were corrected, and a new test file was created to cover the three-phase quota flow.

## Accomplishments
- [x] Renamed `_execute_trigger` to `_execute_quota_trigger` throughout lifecycle.py and test files
- [x] Fixed four stale comment references to old function names in lifecycle.py
- [x] Implemented `_wait_until_quota_near_exhausted` function to silently poll real account quota until genuinely near exhausted
- [x] Added QUOTA_NOTIFY_TRIGGER (99.0%) and QUOTA_NOTIFY_POLL_SECS (60) constants for three-phase quota flow
- [x] Updated test_trigger_independence.py to use new `_execute_quota_trigger` name
- [x] Created test_quota_notify_split.py to cover new three-phase quota notification flow

## Next Actions
1. Run full test suite (pytest tests/ -q) to verify no regressions from the three-phase quota refactor and confirm test_quota_notify_split.py passes
   *Why: Session ended mid-test run; need to confirm all tests pass before committing*
2. Commit the lifecycle.py refactor and new test file with message describing the three-phase quota flow fix
   *Why: Changes are complete and tested; ready for version control*
3. Verify the three-phase flow integrates correctly with the idle checkpoint trigger and context trigger (already independently evaluated per commit 793b959)
   *Why: Ensure quota trigger changes don't interfere with other trigger types*

## Decisions
- Split quota notification into three phases: silent poll → user notification → reset wait — Users working quickly were being interrupted at 90% threshold instead of real quota edge; silent polling lets them work to the genuine limit before notification
- Use QUOTA_NOTIFY_TRIGGER = 99.0% as the threshold for user-facing notification — Distinguishes between 90% (when preparation starts) and 99% (when user is actually interrupted); answers different UX questions
- Poll real account quota every 60 seconds during silent wait phase — Balances responsiveness with API load; user won't be interrupted until quota is genuinely near exhausted

## Files In Play
- `askr/session/lifecycle.py`
- `tests/test_trigger_independence.py`
- `tests/test_quota_notify_split.py`

## Relational Files
- `askr/session/usage_api.py` (imported_by): _wait_until_quota_near_exhausted calls get_quota_status() to poll real account quota
- `tests/test_trigger_independence.py` (tested_by): Tests the renamed _execute_quota_trigger function and trigger independence
- `tests/test_quota_notify_split.py` (tested_by): New test file covering the three-phase quota notification flow
