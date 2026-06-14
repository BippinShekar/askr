# Handover: bippin

Last updated: 2026-06-14 10:02

*Source of truth: `handover_bippin.json`*


## Task
Evaluate analytics metrics for askr status display — specifically whether 'time saved' is a meaningful metric or if goals-based metrics should replace it

## Discussion
Session focused on understanding how the 'time saved 36m (5 sessions today)' metric is calculated and whether it's useful to users. Discovered the metric is purely wall-clock session duration with no signal about actual work completed, goals achieved, or autonomy level. User challenged the premise: showing time spent on Claude isn't inherently useful, and inferring goals then marking them 'completed' is circular reasoning. No consensus reached on replacement metric — session ended with open question about what signal actually matters.

## Progress
25% complete

## Accomplishments
- ✅ Identified analytics schema limitation: no goals_completed, commit_count, or autonomy tracking — only duration_seconds and session metadata
- ✅ Confirmed 'time saved' calculation is wall-clock duration summed across sessions, not a derived productivity metric
- ✅ Removed Phase 4 (Public Launch) from roadmap.md — deprioritized in favor of Phase 3.11 (JSON Handover Schema)

## Next Actions
1. Define what 'completion' actually means for askr: is it commits merged? goals inferred from git history? user-declared milestones? Pick one signal and design analytics schema to capture it.
   *Why: Current 'time saved' is meaningless without grounding in actual work output. User rejected inferring goals retroactively.*
2. If keeping session duration metric, rename it to 'session time' or 'claude time' and remove 'saved' framing — it's descriptive, not prescriptive.
   *Why: Honest labeling avoids false productivity claims.*
3. Add session UUID to status display for enhanced clarity on which session a metric belongs to — user requested this for debugging.
   *Why: Improves traceability when reviewing analytics across multiple sessions.*
4. Verify context checkpoint cards display correct 'turns remaining' in staging (from OPEN GOALS) — this was deferred but still pending.
   *Why: Unfinished work from earlier session.*

## Decisions
- Removed Phase 4 (Public Launch) from roadmap — deprioritized GitHub launch, brew tap, Twitter thread in favor of Phase 3.11 (JSON Handover Schema) — Focus shifted to internal tooling maturity (handover schema, analytics clarity) before external launch readiness.
- Did not implement goals-based completion metric this session — User identified circular logic: inferring goals retroactively and marking them 'completed' is not a real signal.

## User-Rejected Approaches
- **Display 'time saved' as a productivity metric showing how much time user spent in Claude sessions** — "How would showing the user how much time they spent on claude even be useful?" (domain: analytics.json, status display)
- **Infer goals from session activity and mark them as completed** — "goals done, being the goals inferred majoritily right? so we are going to infer goals and then call them completed?" (domain: analytics schema, completion tracking)

## Failed Approaches
- Grepping codebase for 'time_saved', 'sessions_today', 'completed_goals' to find existing metric definitions — Schema doesn't exist — metrics are ad-hoc calculations in status display, not tracked in analytics.json.
- Assuming 'time saved' was a derived metric (e.g., time saved vs manual work) — It's just wall-clock duration — no baseline or comparison.

## Files In Play
- `roadmap.md`
- `askr_state/analytics.json`
- `logger.py`
- `cmd_init()`

## Relational Files
- `logger.py` (configures): Contains log_line_mark() and cost_since_mark() — the cost tracking infrastructure that feeds analytics.
- `askr_state/analytics.json` (imported_by): Ground truth for session metrics; schema needs redesign to support meaningful completion signals.
- `status display / morning report` (configures): Consumes analytics.json to show 'time saved' — needs metric redesign before display changes.

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`

## Blockers
- No consensus on what metric should replace 'time saved' — requires product decision on what 'completion' means (commits? user-declared goals? inferred milestones?).
