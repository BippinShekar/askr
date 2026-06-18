# Handover: bippin

Last updated: 2026-06-18 20:22

*Source of truth: `handover_bippin.json`*


## Task
Refined investor outreach strategy for Leaps by evaluating KAE Capital's investment thesis and drafting problem-first emails, and identified critical structural bugs in askr daemon behavior around companion terminal spawning (0% context ghost entries) and concurrent session auto-open race conditions causing poor UX.

## Discussion
User is in active fundraising mode with outreach to Together Fund, KAE Capital, and PI Ventures. Prior sessions completed KAE Capital email drafts by rejecting all hiring-infrastructure framing as fundamentally misaligned with investor conviction. Critical realization: the authentic problem Leaps solves is 'AI replaced effort everywhere except the one place people actually need it'—a thesis about where automation has failed to penetrate. This session pivoted to investigating askr daemon behavior: user provided visual evidence that newly spawned companion terminals appear at 0% context despite auto-start mechanism, and that new sessions auto-open while current sessions are still running, creating confusing UX. Investigation confirmed these are pre-existing structural bugs in session lifecycle and daemon trigger logic, not race conditions.

## Accomplishments
- [x] Researched KAE Capital's investment thesis and historical portfolio (Porter, Zetwerk, InMobi) to inform messaging strategy
- [x] Identified user's core messaging principle: problem-first framing over self-promotional positioning
- [x] Rejected spray-and-pray outreach approach (deals@together.fund email) based on timing and signal risk
- [x] Validated that hiring-infrastructure messaging does not resonate with KAE Capital's actual investment priorities
- [x] Rejected all hiring-tech subject line variants as fundamentally misaligned with investor conviction, not just messaging optimization
- [x] Identified emerging authentic problem statement: 'AI replaced effort everywhere except the one place people actually need it'
- [x] Conducted research on KAE Capital's actual investment thesis (overlooked infrastructure sectors, B2B supply chains, intelligent automation) to differentiate from Together Fund approach
- [x] Rejected multiple subject line options ('Why does only one side of hiring have infrastructure?', 'The candidate side of hiring has no Eightfold', '$35B hiring market') as self-promotional rather than problem-centric
- [x] Drafted short, direct emails to Shivam (Analyst) and Gaurav (GP) at KAE Capital with contrast-based subject line ('AI writes your emails now. It still can't get you hired.') leading with authentic problem statement, fit-scoring mechanism, and deck link
- [x] Confirmed PI Ventures outreach strategy using YC subject line and email body for info@piventures.in
- [x] Investigated askr daemon behavior around context-triggered companion terminal spawning and session initialization state
- [x] Examined session lifecycle, signal handling, terminal initialization logic, and handover state propagation to identify root cause of 0% context ghost entries
- [x] Confirmed via daemon logs that 0% context entries are permanent ghost entries in legacy per-project state, not one-time race conditions
- [x] Identified concurrent session auto-open bug: new sessions spawn while current session is running, creating UX confusion instead of waiting for session completion

## In Progress
- `askr/hooks/session_start.py` (line 260): Fix legacy per-project state rewrite logic that creates 0% context ghost entries in companion terminal initialization
- `askr/daemon/trigger.py`: Implement session-completion wait logic before auto-opening new companion terminals to prevent concurrent session race condition

## Next Actions
1. Locate and examine askr/daemon/trigger.py to understand how auto-open decisions are made and add session-completion check before spawning new companion terminal
   *Why: User explicitly flagged that new sessions should not auto-open while current session is running; this is a UX blocker and requires daemon-level fix*
2. Fix askr/hooks/session_start.py line 220-260 region: remove or correct the legacy per-project state rewrite that creates permanent 0% context ghost entries
   *Why: Confirmed structural bug via daemon logs; newly spawned terminals should inherit handover context, not reset to 0%*
3. Add integration test covering: (a) session auto-start from handover preserves context percentage, (b) new companion terminal does not spawn until prior session completes
   *Why: Both bugs are pre-existing and will regress without test coverage*
4. Resume investor outreach: send KAE Capital emails to Shivam and Gaurav with problem-first subject line and deck link once askr stability is confirmed
   *Why: Fundraising is active; askr bugs are blocking confidence in tool reliability for sustained outreach work*

## Decisions
- Rejected hiring-infrastructure messaging as core positioning for KAE Capital outreach — KAE Capital's actual investment thesis focuses on overlooked infrastructure sectors and B2B supply chains, not hiring tech; messaging must align with investor conviction, not spray-and-pray
- Rejected Together Fund spray-and-pray email (deals@together.fund) as timing and signal risk — User is in active, targeted fundraising mode; generic outreach dilutes signal and wastes relationship capital
- Adopted problem-first framing ('AI replaced effort everywhere except the one place people actually need it') as core authentic positioning — Resonates with actual user conviction and differentiates from self-promotional hiring-tech messaging
- Identified askr daemon bugs as pre-existing structural issues, not race conditions introduced this session — Confirmed via daemon logs and code inspection; requires architectural fix to session lifecycle and trigger logic

## User-Rejected Approaches
- **Concurrent session auto-open while current session is running** — "it should wait for this session to complete and then auto open cause that would make the user confused, and is bad UX" (domain: askr/daemon/trigger.py)

## Failed Approaches
- Investigated 0% context as one-time race condition in terminal initialization — Daemon logs revealed it is a permanent ghost entry created by legacy per-project state rewrite logic in session_start.py, not a transient race
- Searched for signal handling or kill logic as root cause of context loss — Root cause is not signal handling but state rewrite logic that overwrites handover context on session start

## Files In Play
- `askr/hooks/session_start.py`
- `askr/daemon/trigger.py`
- `askr/session/lifecycle.py`

## Relational Files
- `askr_state/handover_bippin.json` (configures): Session start hook reads and rewrites this file; 0% context bug originates in how handover state is propagated to new terminals
- `askr/daemon/lifecycle.py` (imported_by): Session lifecycle management; signal handling and terminal initialization logic examined during investigation
- `~/Library/Logs/askr/daemon.log` (configures): Daemon logs confirmed 0% context ghost entries are permanent, not transient; provided ground truth for bug confirmation

## Uncommitted Files
- `.askr_history`
- `askr_state/implementation_bippin.jsonl`

## Blockers
- askr daemon spawns new companion terminals at 0% context despite auto-start from handover; blocks confidence in tool reliability for sustained fundraising work
- askr daemon auto-opens new sessions while current session is running, creating UX confusion; requires session-completion wait logic in trigger
