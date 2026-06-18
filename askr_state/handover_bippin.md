# Handover: bippin

Last updated: 2026-06-18 20:18

*Source of truth: `handover_bippin.json`*


## Task
Refined investor outreach strategy for Leaps by evaluating KAE Capital's investment thesis, rejecting hiring-infrastructure messaging as unmarketable, identifying need for problem-first positioning, discovering core insight that AI automation has failed to penetrate the one domain where people actually need it, drafting direct emails to KAE Capital contacts (Shivam and Gaurav) with authentic problem-statement subject lines, and preparing PI Ventures outreach using YC subject line and email body. This session investigated askr daemon behavior around context-triggered companion terminal spawning and session initialization state.

## Discussion
User is in active fundraising mode with outreach to Together Fund, KAE Capital, and PI Ventures. Prior sessions completed KAE Capital email drafts by rejecting all hiring-infrastructure framing as fundamentally misaligned with investor conviction. Critical realization: the authentic problem Leaps solves is 'AI replaced effort everywhere except the one place people actually need it'—a thesis about where automation has failed to penetrate. Session produced draft emails for Shivam (Analyst) and Gaurav (GP) at KAE Capital with contrast-based subject line ('AI writes your emails now. It still can't get you hired.') that lead with real problem, not self-promotion. This session pivoted to investigating askr's daemon behavior: user observed that newly spawned companion terminals appear at 0% context despite auto-starting from handover, which contradicts expected behavior. Investigation examined session lifecycle, signal handling, and terminal initialization logic but did not identify root cause.

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

## In Progress
- `None`: Diagnose why newly spawned companion terminals appear at 0% context despite auto-starting from handover state; investigate session lifecycle, signal handling, and terminal initialization logic

## Next Actions
1. Send drafted KAE Capital emails to shivam@kae-capital.com and gaurav@kae-capital.com with subject 'AI writes your emails now. It still can't get you hired.' and body emphasizing stateless vs. compound fit-scoring automation
   *Why: Emails are drafted and ready; timing is critical for investor outreach during active fundraising window*
2. Research PI Ventures partner names and send email to named contact (or info@piventures.in if individual names unavailable) using YC subject line and email body
   *Why: PI Ventures is third priority investor; outreach strategy is prepared and ready to execute*
3. Examine askr/session/lifecycle.py signal handling and askr/cli/askr.py terminal spawning logic to identify why companion terminals initialize at 0% context instead of inheriting handover state
   *Why: User observation indicates companion terminals are not properly loading checkpoint state on spawn; this breaks the core daemon guarantee of continuous work resumption*
4. Verify that new companion terminal sessions are reading from correct handover file path and that state_dir is threaded through session initialization
   *Why: Prior commits (019150e, 7149ac3) fixed state_dir threading in goals/lifecycle; companion spawn may have missed this fix*

## Decisions
- Rejected all hiring-infrastructure positioning for KAE Capital outreach — User explicitly stated 'I don't think anyone is moved with hiring tech/ai bullshit'—this framing is fundamentally misaligned with investor conviction, not a messaging optimization problem
- Adopted problem-first, contrast-based subject line ('AI writes your emails now. It still can't get you hired.') for KAE Capital emails — Leads with authentic problem statement (where AI automation has failed to penetrate) rather than self-promotion; aligns with user's core messaging principle and investor's actual investment thesis
- Rejected spray-and-pray outreach to Together Fund deals@ address — Timing risk and signal cost too high; KAE Capital and PI Ventures are higher-conviction targets with clearer fit

## Failed Approaches
- Hiring-infrastructure messaging variants ('Why does only one side of hiring have infrastructure?', 'The candidate side of hiring has no Eightfold', '$35B hiring market') — All variants were self-promotional rather than problem-centric; user rejected the entire hiring-tech positioning as unmarketable to investors

## Relational Files
- `askr/session/lifecycle.py` (imported_by): Signal handling and session termination logic may affect companion terminal spawning behavior
- `askr/cli/askr.py` (imported_by): Main entry point and terminal spawning logic; _statusline_text() and companion terminal initialization live here
- `askr/ide/vscode-extension/extension.js` (configures): VS Code extension may influence how companion terminals are spawned or initialized

## Blockers
- Companion terminals spawning at 0% context despite auto-starting from handover state; root cause not yet identified
