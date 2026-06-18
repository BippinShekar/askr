# Handover: bippin

Last updated: 2026-06-18 20:01

*Source of truth: `handover_bippin.json`*


## Task
Built askr, a Claude session checkpoint and resume system for developers, completing 4 implementation stages (blockers aggregation, state isolation, checkpoint merging, and observability hardening) with 37 passing tests and identified a regression in the VS Code extension's context percentage display showing 0% despite active session work.

## Discussion
This session focused on shipping the final 4 stages of askr's core infrastructure: Stage 1 wired blockers aggregation from per-dev handover files instead of a dead shared file, Stage 2 isolated goals state per developer, Stage 3 merged checkpoint decisions and failed approaches, and Stage 4 hardened observability by stopping exception swallowing. All 37 tests pass. User then discovered a regression where the VS Code extension displays 0% context usage despite active work, triggering investigation into stats file reading and context percentage calculation in the extension.

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
- [x] Implemented Stage 1: wired load_blockers() and _infer_direction Signal 2 to aggregate per-dev handover_<dev>.json blockers instead of dead shared blockers.md file, eliminating write race condition
- [x] Implemented Stage 2: isolated goals state per developer by threading state_dir through goal lifecycle call sites
- [x] Implemented Stage 3: merged checkpoint decisions and failed approaches from handover documents
- [x] Implemented Stage 4: hardened observability by stopping exception swallowing in failure paths
- [x] Added comprehensive test coverage: test_goals.py, test_blockers.py, test_checkpoint_merge.py bringing total test suite from 15 to 37 passing tests
- [x] Committed all 4 stages and pushed to git with clean test suite
- [x] Investigated VS Code extension context percentage display showing 0% despite active session work by searching for context_pct, session_stats, and stats file reading logic

## In Progress
- `askr/ide/vscode-extension/extension.js`: Debugging context percentage display regression showing 0% despite active session work; investigating stats file reading, context_pct calculation, and session_stats path resolution

## Next Actions
1. Examine askr/ide/vscode-extension/extension.js to locate context_pct calculation and session_stats file reading logic; check if stats file path is correctly resolved or if stats are being read before they're written
   *Why: User reported 0% context display despite active work; this is a regression introduced in recent changes and blocks accurate session monitoring in the IDE*
2. Check ~/.config/askr/stats/ directory structure and verify that stats files are being written with correct format and timing relative to extension reads
   *Why: Stats file may not exist, be malformed, or be read before write completes; need to confirm file I/O contract*
3. Review recent changes to stats file writing or path handling in askr/cli or askr/checkpoint modules to identify what broke context percentage calculation
   *Why: Regression was introduced in this session's changes; need to identify which stage (1-4) or prior commit caused the issue*
4. Send drafted KAE Capital emails to shivam@kae-capital.com and gaurav@kae-capital.com with subject 'AI writes your emails now. It still can't get you hired.' and body emphasizing stateless vs. compound fit-scoring automation
   *Why: Emails are drafted and ready; timing is critical for investor outreach during active fundraising window*
5. Research PI Ventures partner names and send email to named contact (or info@piventures.in if names unavailable) using YC subject line and email body
   *Why: PI Ventures outreach strategy confirmed; need to execute with personalized contact if possible*

## Decisions
- Rejected hiring-infrastructure messaging entirely as fundamentally misaligned with investor conviction — User stated 'I don't think anyone is moved with hiring tech/ai bullshit' — signals complete pivot away from hiring market positioning
- Adopted problem-first positioning: 'AI replaced effort everywhere except the one place people actually need it' — Authentic problem statement that resonates with investor thesis about where automation has failed to penetrate
- Rejected spray-and-pray outreach to Together Fund deals@together.fund — Timing and signal risk; better to focus on targeted outreach to KAE Capital and PI Ventures with problem-centric messaging
- Used contrast-based subject line for KAE Capital: 'AI writes your emails now. It still can't get you hired.' — Leads with real problem, not self-promotion; aligns with KAE's investment thesis in overlooked infrastructure sectors
- Implemented blockers aggregation from per-dev handover files instead of shared blockers.md — Eliminates write race condition and provides per-developer isolation of blocker state
- Threaded state_dir through goal lifecycle to isolate goals state per developer — Prevents cross-developer state pollution and enables proper checkpoint/resume semantics

## User-Rejected Approaches
- **Multiple hiring-tech subject lines: 'Why does only one side of hiring have infrastructure?', 'The candidate side of hiring has no Eightfold', '$35B hiring market'** — "All rejected as self-promotional rather than problem-centric; user stated 'I don't think anyone is moved with hiring tech/ai bullshit'" (domain: investor outreach messaging)

## Failed Approaches
- Spray-and-pray outreach to Together Fund deals@together.fund — Timing and signal risk; better to focus on targeted outreach with problem-centric messaging
- Shared blockers.md file for aggregating blocker state across developers — Write race condition and lack of per-developer isolation; replaced with per-dev handover_<dev>.json aggregation

## Files In Play
- `askr/ide/vscode-extension/extension.js`
- `tests/test_goals.py`
- `tests/test_blockers.py`
- `tests/test_checkpoint_merge.py`
- `askr/checkpoint.py`
- `askr/cli/ask.py`

## Relational Files
- `askr_state/handover_bippin.json` (imported_by): Per-dev handover file used for blockers aggregation and state isolation
- `~/.config/askr/stats/` (configures): Stats directory where session stats are written and read by VS Code extension; context percentage regression points to this path
- `askr/checkpoint.py` (imports): Core checkpoint logic for merging decisions and failed approaches from handover documents
- `tests/test_goals.py` (tested_by): Tests goals state isolation per developer
- `tests/test_blockers.py` (tested_by): Tests blockers aggregation logic from per-dev handover files
- `tests/test_checkpoint_merge.py` (tested_by): Tests checkpoint merge of decisions and failed approaches

## Blockers
- VS Code extension displays 0% context usage despite active session work; regression introduced in this session's changes; need to identify root cause in stats file reading or context_pct calculation
