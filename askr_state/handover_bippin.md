# Handover: bippin

Last updated: 2026-06-14 10:00

*Source of truth: `handover_bippin.json`*


## Task
Investigate and fix the 'time saved' metric display in askr status — currently shows wall-clock session duration, not actual productivity value

## Discussion
User challenged the validity of the 'time saved 36m (5 sessions today)' metric, correctly noting it's just summed session durations with no actual productivity measurement. Session ended mid-investigation: attempted to locate analytics.json and goals_completed tracking to understand what data exists. User wants either a proper metric (e.g., goals completed, context reused, API calls avoided) or honest alternative display. No resolution reached; investigation incomplete.

## Progress
15% complete

## Accomplishments
- ✅ Identified root cause: 'time saved' is purely wall-clock duration from session_start.json → analytics.json, not tied to any outcome metric
- ✅ Confirmed analytics.json exists and contains duration_seconds entries

## In Progress
- `askr/cli/askr.py`: Investigating today_summary() function to understand current metric calculation and identify where to inject real productivity data
- `askr_state/analytics.json`: Attempting to read and parse to see what fields are currently tracked (duration_seconds confirmed, goals_completed unknown)

## Next Actions
1. Read askr/cli/askr.py and locate today_summary() function — extract exact logic for 'time saved' calculation and identify where metric source comes from
   *Why: Need to see current implementation before deciding whether to replace metric or add new field*
2. Check if goals_completed, tasks_done, or similar outcome fields exist anywhere in codebase (grep -rn 'goals_completed\|tasks_done\|completed_count' askr/)
   *Why: User wants real productivity metric; must know if tracking infrastructure exists or needs to be built*
3. Propose 3 alternative metrics to user: (A) 'goals completed today', (B) 'context reused (sessions with prior state loaded)', (C) 'API calls avoided via caching' — with honest assessment of which is measurable now
   *Why: User explicitly rejected vague 'time saved' and wants brutal honesty; need concrete options with feasibility*
4. If no outcome tracking exists: add minimal goals_completed counter to session_end hook (user marks goal done/skip before exit) and wire to analytics.json
   *Why: Fastest path to real metric without major refactor*
5. Update status display to show chosen metric (or revert to 'session duration' if no better data available) and commit with clear reasoning in commit message
   *Why: Close the loop; user wants clarity, not misleading numbers*

## Decisions
- Do not keep 'time saved' as-is without outcome backing — User correctly identified it as meaningless wall-clock duration; continuing would undermine credibility
- Investigate existing tracking before building new infrastructure — May already have goals_completed or similar; avoid duplicate work

## User-Rejected Approaches
- **Implied: keep 'time saved 36m' as current metric** — "then we need to either come up with proper metric here, or display something else right" (domain: askr/cli/askr.py (status display))

## Failed Approaches
- Grepped for completed_goals, goals_completed, done_today — commands ran but output not captured/parsed — Bash tool calls incomplete; piped Python parsing not executed successfully

## Files In Play
- `askr/cli/askr.py`
- `askr_state/analytics.json`
- `askr/utils/logger.py`

## Relational Files
- `askr/utils/logger.py` (imported_by): Contains log_line_mark() and cost_since_mark() added this session; may need extension for outcome tracking
- `askr_state/implementation_state.md` (configures): Tracks session state; may need to log which metric decision was made

## Uncommitted Files
- `askr_state/implementation_state.md`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Unknown: does goals_completed or outcome tracking already exist in codebase? Must grep/read to proceed
