# Handover: bippin

Last updated: 2026-07-06 19:27

*Source of truth: `handover_bippin.json`*


## Task
Diagnosed and fixed three critical bugs in activity tracking, handover generation, and session continuity that were causing false inactivity alerts, incorrect quota announcements, and unwanted session auto-launches.

## Discussion
The askr system had three interconnected bugs: (1) idle trigger (Trigger C) was being announced as a quota emergency and auto-launching new sessions, (2) the idle threshold was measuring time since last completed turn rather than actual user inactivity, and (3) session continuity via the stop hook was not preserving stage-plan context when autonomous jobs ran between user interactions. This session diagnosed root causes in lifecycle.py and identified that code-path reuse across different trigger types (quota, context, idle) was causing semantic mismatches. The user clarified that the continuity problem extends beyond mid-session companion opens to include autonomous handover jobs that run after context-switch stops.

## Accomplishments
- [x] Diagnosed false 'inactive 10 min' + false 'pushed to git' as two separate bugs in lifecycle.py idle trigger logic
- [x] Confirmed idle trigger was misannounced as quota emergency and auto-launched sessions due to code-path reuse in _execute_trigger()
- [x] Fixed idle trigger to use dedicated _checkpoint_idle_inactivity() function instead of generic _execute_trigger()
- [x] Documented that voice broadcast should fire only on emergency conditions (quota/context at 90%+), never per-turn
- [x] Confirmed OAuth cost tracking uses real quota_five_hour_pct for new calls, real cost_usd for historical entries
- [x] Verified ask CLI uses separate API key, not Claude Code's OAuth token

## In Progress
- `askr/session/lifecycle.py`: Session continuity for autonomous handover jobs — preserving stage-plan context when stop hook triggers background saves and autonomous next-step decisions

## Next Actions
1. Trace the stop hook's _start_claude() call path to understand how stage-plan context is (or is not) passed to autonomous handover jobs
   *Why: User reported that multi-step stage plans lose context when a context-switch stop happens mid-implementation; autonomous jobs run without knowledge of remaining stages*
2. Verify idle threshold in lifecycle.py:129,140 is measuring actual user app inactivity, not time since last completed turn
   *Why: Original bug report showed false 'inactive 10 min' alerts during active reading/thinking; the semantics of IDLE_TRIGGER_SECS must reflect real user absence, not turn completion*
3. Test voice announcement pipeline with quota/context at 90%+ to confirm emergency-only broadcast is working correctly
   *Why: Voice subsystem was changed to announce only on genuine emergencies; production verification needed to ensure no spam and correct alert firing*
4. Monitor production quota tracking to verify OAuth calls report real quota_five_hour_pct and historical entries retain cost_usd
   *Why: Cost tracking was refactored to handle OAuth's lack of per-call cost data; audit trail and rate-limit visibility must be accurate*

## Decisions
- OAuth-authenticated calls (Claude Code's token) report real quota_five_hour_pct, not fabricated cost_usd — OAuth token does not provide per-call cost data; quota % is the only meaningful metric available; fabricating $ amounts is misleading
- Historical billed entries (pre-OAuth) retain real cost_usd; new OAuth entries use quota_five_hour_pct — Preserves audit trail of actual billing; OAuth calls have no per-call cost, only quota consumption
- `ask <query>` CLI command uses a separate API key, not Claude Code's OAuth token — Isolates user queries from Claude Code's quota; prevents user queries from exhausting the OAuth token's rate limit
- Voice broadcast fires only on emergency conditions (quota/context at 90% or genuine user inactivity), never per-turn — Prevents announcement spam; users only hear alerts when system state genuinely requires attention
- Idle trigger (Trigger C) uses dedicated _checkpoint_idle_inactivity() function, not generic _execute_trigger() — Prevents code-path reuse bugs; idle conditions have different semantics than quota/context emergencies (no quota-waiting, no session auto-launch)

## User-Rejected Approaches
- **Debouncing continuous per-turn checkpoints to reduce frequency while keeping the hook active** — "User rejected the entire continuous-checkpoint model; the problem is not frequency but the fundamental design of checkpointing on every turn, which blocks user interaction" (domain: askr/session/lifecycle.py)

## Failed Approaches
- Implementing project-root-based path locking to prevent nested worktree cwd-drift lockout — Conflicts with desired architecture: system must support multi-repo concurrent execution from single terminal, which requires cross-repo execution guards to be permissive rather than restrictive
- Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds() — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire
- Debouncing continuous per-turn checkpoints to reduce frequency while keeping the hook active — User rejected the entire continuous-checkpoint model; the problem is not frequency but the fundamental design of checkpointing on every turn, which blocks user interaction
- Reusing _execute_trigger() for all three trigger types (quota, context, idle) — Idle conditions have different semantics than quota/context emergencies; code-path reuse caused misannouncement and unwanted session auto-launch

## Files In Play
- `askr/session/lifecycle.py`
- `askr_state/decisions.jsonl`
- `askr_state/failed_approaches.md`
- `askr_state/goals.jsonl`

## Relational Files
- `askr/session/lifecycle.py` (imports): Contains idle trigger logic, voice announcement dispatch, and session auto-launch code that were the root cause of the three bugs
- `askr/voice/announce.py` (imported_by): Voice broadcast subsystem that was firing incorrectly on idle triggers; now restricted to emergency conditions only
- `askr/cost/tracker.py` (imported_by): OAuth cost tracking was refactored to report real quota_five_hour_pct instead of fabricated cost_usd
- `askr/cli/ask.py` (imported_by): CLI ask command was moved to separate API key to isolate from Claude Code's OAuth quota

## Blockers
- Session continuity for autonomous handover jobs — stage-plan context loss when stop hook triggers mid-implementation needs investigation of _start_claude() call path
