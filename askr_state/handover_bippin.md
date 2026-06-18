# Handover: bippin

Last updated: 2026-06-18 19:35

*Source of truth: `handover_bippin.json`*


## Task
Refined investor outreach strategy for Leaps by evaluating KAE Capital's investment thesis, rejecting hiring-infrastructure messaging as unmarketable, identifying need for problem-first positioning, discovering core insight that AI automation has failed to penetrate the one domain where people actually need it, drafting direct emails to KAE Capital contacts (Shivam and Gaurav) with authentic problem-statement subject lines, and preparing PI Ventures outreach using YC subject line and email body. Hardened askr daemon codebase by threading state_dir through checkpoint.py, lifecycle.py, goals.py, and writer.py to eliminate ambient-cwd fallback in multi-project contexts, corrected LLM prompt constraints to forbid self-referential handover file references and invented session_metadata keys, and reinforced in_progress.file schema to reject handover/state files as work-in-progress targets.

## Discussion
User is in active fundraising mode with outreach to Together Fund, KAE Capital, and PI Ventures. Prior sessions completed KAE Capital email drafts by rejecting all hiring-infrastructure framing as fundamentally misaligned with investor conviction. Critical realization: the authentic problem Leaps solves is 'AI replaced effort everywhere except the one place people actually need it'—a thesis about where automation has failed to penetrate. This session completed the multi-project state isolation fix by discovering and patching two missed call sites in checkpoint.py (_generate_project_brief → load_open_goals) and lifecycle.py (_get_next_goal), both reading goals via ambient cwd in daemon context. Also hardened LLM handover prompt to forbid in_progress.file from pointing at handover/state files and session_metadata from containing invented keys beyond trigger_type and timestamp. User then asked for brutal honesty on askr readiness across four dimensions: multi-repo init, co-founder collaboration, installation ease, and handover/checkpoint quality.

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
- [x] Fixed repo-isolation in checkpoint.py by threading state_dir through git_commit_push() and create_checkpoint() to eliminate ambient-cwd fallback in multi-project daemon contexts
- [x] Discovered and patched two missed call sites in checkpoint.py (_generate_project_brief → load_open_goals) and lifecycle.py (_get_next_goal) that were reading goals via ambient cwd instead of state_dir
- [x] Hardened LLM handover prompt in checkpoint.py to forbid in_progress.file from pointing at handover/state files and session_metadata from containing invented keys beyond trigger_type and timestamp
- [x] Reinforced in_progress.file schema documentation to clarify that only real source files should be listed, never handover/state files themselves, and null is acceptable for non-code work

## In Progress
- `askr/session/checkpoint.py` (line 703): Verify all subprocess calls in git_commit_push() now pass cwd parameter; ensure state_dir threading is complete through create_checkpoint() and _generate_project_brief()
- `askr/session/lifecycle.py`: Verify _get_next_goal() and all goal-loading call sites now receive state_dir parameter instead of relying on ambient cwd
- `askr/state/goals.py`: Verify load_open_goals() signature accepts state_dir and uses it consistently; check all callers pass it
- `askr/state/writer.py`: Verify write_goal() and related functions accept state_dir and do not fall back to ambient cwd

## Next Actions
1. Commit the checkpoint.py, lifecycle.py, goals.py, writer.py state_dir threading fixes and LLM prompt hardening with message 'fix(daemon): complete state_dir threading and handover schema validation'
   *Why: Unblock multi-project daemon stability and prevent future handover schema violations*
2. Run askr init in a separate test repo (not the Leaps repo) to verify multi-repo isolation works end-to-end: confirm state_dir is correctly resolved, checkpoints land in the right askr_state/, and no cross-repo contamination occurs
   *Why: Validate that the state_dir threading fixes actually solve the multi-project problem before claiming readiness*
3. Audit install.sh and askr init flow for co-founder onboarding: verify gitattributes setup, .gitignore rules, and initial state file creation are idempotent and non-destructive
   *Why: User asked if co-founder can safely run askr init in startup repo; need to confirm no data loss or permission issues*
4. Document the four readiness dimensions (multi-repo init, co-founder collab, install ease, handover quality) in a READINESS.md file with honest assessment of each, including known gaps and workarounds
   *Why: User asked for brutal honesty on readiness; formalize the answer so it's visible and updatable*
5. Send KAE Capital emails to Shivam and Gaurav with the drafted subject line and body; track response timing and signal
   *Why: Investor outreach is time-sensitive; emails are ready and authentic problem framing is validated*

## Decisions
- Reject hiring-infrastructure messaging entirely for KAE Capital outreach — KAE's portfolio (Porter, Zetwerk, InMobi) and stated thesis focus on overlooked infrastructure sectors and B2B supply chains, not hiring tech. Hiring-infrastructure framing is self-promotional and misaligned with their conviction.
- Adopt problem-first positioning: 'AI replaced effort everywhere except the one place people actually need it' — Authentic problem statement that resonates with KAE's infrastructure-first mindset and differentiates from Together Fund's hiring-tech angle
- Use contrast-based subject line for KAE Capital: 'AI writes your emails now. It still can't get you hired.' — Leads with the authentic problem (AI's failure to penetrate hiring), not self-promotion; signals that Leaps solves a real gap
- Thread state_dir through all daemon-context goal-loading and git operations to eliminate ambient-cwd fallback — Multi-project daemon must never read/write state for the wrong project; ambient cwd is unreliable in concurrent contexts
- Forbid in_progress.file from pointing at handover/state files; allow null for non-code work — Handover/state files are outputs of the checkpoint process, not work in progress. Prevents circular references and clarifies the schema.
- Restrict session_metadata to only trigger_type and timestamp; forbid invented keys — Prevents LLM from adding ad-hoc metadata that breaks schema validation and makes handover parsing fragile

## User-Rejected Approaches
- **Spray-and-pray outreach to deals@together.fund with generic hiring-tech pitch** — "Rejected based on timing risk and signal quality; user prioritized targeted, authentic outreach to KAE Capital and PI Ventures" (domain: investor outreach strategy)
- **Multiple hiring-tech subject lines ('Why does only one side of hiring have infrastructure?', 'The candidate side of hiring has no Eightfold', '$35B hiring market')** — "Rejected as self-promotional and misaligned with investor conviction; user insisted on problem-first framing" (domain: KAE Capital email messaging)

## Failed Approaches
- Hiring-infrastructure positioning for KAE Capital outreach — KAE's portfolio and thesis focus on overlooked infrastructure sectors and B2B supply chains, not hiring tech. Messaging was self-promotional and misaligned with their conviction.
- Relying on ambient cwd in daemon context for goal-loading and git operations — Multi-project daemon can have multiple projects in flight; ambient cwd is unreliable and causes cross-project state contamination
- Allowing LLM to invent session_metadata keys beyond trigger_type and timestamp — Breaks schema validation and makes handover parsing fragile; LLM should not extend the schema without explicit instruction

## Files In Play
- `askr/session/checkpoint.py`
- `askr/session/lifecycle.py`
- `askr/state/goals.py`
- `askr/state/writer.py`

## Relational Files
- `askr/state/config.py` (imported_by): Provides get_state_dir() which checkpoint.py and lifecycle.py use to resolve state_dir; critical for multi-project isolation
- `askr/cli/askr.py` (imports): Entry point for askr init and daemon; must pass state_dir correctly to all downstream functions
- `install.sh` (configures): Sets up gitattributes and initial state; user asked about co-founder onboarding readiness
- `askr_state/implementation_bippin.jsonl` (tested_by): Uncommitted checkpoint log; contains evidence of state_dir threading fixes

## Uncommitted Files
- `askr/session/checkpoint.py`
- `askr/session/lifecycle.py`
- `askr/state/goals.py`
- `askr/state/writer.py`
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Multi-repo init not yet validated end-to-end; state_dir threading fixes are in place but need integration test
- Co-founder onboarding readiness not yet assessed; install.sh and gitattributes setup need audit for idempotency and safety
- Installation ease not yet documented; no clear guidance on dependencies, Python version, or troubleshooting
