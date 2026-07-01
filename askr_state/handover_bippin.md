# Handover: bippin

Last updated: 2026-07-02 01:22

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, and identified that Homebrew tap installation requires full namespace (brew install BippinShekar/askr/askr) rather than simple brew install askr.

## Discussion
Askr has progressed through three major phases: Phase 3 (notifications) and Phase 3.5 (permission guard) are fully implemented and tested; Phase 4 (approval workflow) is wired into the Cursor extension. The v0.1.0 release cycle was completed by computing the real tarball sha256, fixing the Homebrew formula to reference the correct GitHub release artifact, creating the homebrew-askr tap repository, and verifying end-to-end installation. This session confirmed the tap works but revealed that users must use the full namespace `brew install BippinShekar/askr/askr` rather than the simpler `brew install askr` — the latter would require submitting the formula to Homebrew's core tap, which is a separate process. Critical gap remains: guard_warning notification type is not wired into Cursor extension.js type whitelist, so Phase 3.5 IDE popups do not render despite being marked Done in roadmap. README.md still lists Phase 3 and 3.5 as 'Coming Next' and requires update to reflect completion.

## Accomplishments
- [x] LinkedIn location combobox field filling fixed with city name extraction and fallback retry pattern
- [x] Identified root cause of LinkedIn location field failures: full location strings do not trigger city autocomplete dropdown
- [x] Implemented two-part fix: prompt instructs extraction of city name from full location string, with retry on failure
- [x] Killed orphaned uvicorn process blocking backend logs
- [x] Conducted comprehensive security audit of apply agent code generation paths with four hardening fixes against prompt injection attacks
- [x] Fixed resume PDF portfolio URL lookup from qa_bank.portfolio_url to application_prefill.answers.portfolio_url
- [x] Updated PDF generator to render 'Portfolio' as link label instead of domain URL
- [x] Diagnosed Ramp application failure as Ashby spam_warning state (browser fingerprinting-based anti-bot detection)
- [x] Implemented spam_warning recovery with 'Learn more' probe to locate submit/submit-again button
- [x] Extended spam_warning handling to distinguish overlay banner (resubmit after scroll) vs form replacement (hard refresh required)
- [x] Refactored spam recovery strategy to defer spam-flagged jobs to end of session instead of inline retry
- [x] Investigated queue drain architecture and browser_stream replay buffer lifecycle
- [x] Implemented permission_gate.py to detect dangerous permissions (skip-permissions, unrestricted Bash, rm in allow list)
- [x] Implemented session_start.py to hold queued tasks instead of auto-injecting when dangerous permissions detected
- [x] Wired task_approval_pending notification type into Cursor extension.js for IDE popup rendering
- [x] Added test_permission_gate.py with 13 passing tests covering all dangerous permission detection scenarios
- [x] Added test_task_approval_gate.py with full coverage for approval gate workflow
- [x] Updated roadmap.md to reflect Phase 3.5 (guard) completion and Phase 4 (approval workflow) status
- [x] Auto-completed 'dangerously-skip-permissions sessions before queued' goal via permission gate implementation
- [x] Tagged v0.1.0 release and created GitHub Release artifact
- [x] Computed real sha256 of v0.1.0 tarball and updated Homebrew formula
- [x] Created homebrew-askr tap repository with Formula/askr.rb
- [x] Fixed Homebrew formula lint issues in test block and verified brew audit passes
- [x] Verified end-to-end installation via homebrew-askr tap (brew install BippinShekar/askr/askr)
- [x] Confirmed both ask and askr binaries execute correctly post-installation

## Next Actions
1. Wire guard_warning notification type into Cursor extension.js type whitelist so Phase 3.5 permission guard IDE popups render when dangerous permissions are detected
   *Why: Phase 3.5 is marked complete in roadmap but guard_warning popups do not appear in IDE; this is the final blocker for Phase 3.5 user-facing functionality*
2. Update README.md to reflect that Phase 3 (notifications) and Phase 3.5 (permission guard) are complete and deployed, not 'Coming Next'
   *Why: Documentation is out of sync with implementation; users and contributors need accurate status*
3. Extend pre_tool_use.py cross-repo boundary check to cover Bash tool calls, not just Write/Edit/MultiEdit operations
   *Why: Currently only file edits are checked for cross-repo violations; Bash commands can also reference foreign repositories and should be guarded*
4. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint (trigger_type==emergency branch)
   *Why: Emergency handovers currently use static boilerplate instead of generating proper context; this reduces handover quality when sessions are interrupted*
5. Document Homebrew installation process: users must use full namespace (brew install BippinShekar/askr/askr) or submit formula to Homebrew core tap for simple brew install askr
   *Why: User asked about simpler installation; clarifying the trade-off between tap-based installation (works now) vs core tap submission (requires Homebrew review process)*

## Decisions
- Homebrew installation via custom tap (BippinShekar/askr) rather than submitting to Homebrew core tap — Custom tap allows immediate distribution without Homebrew review process; users can install with brew tap + brew install; core tap submission is deferred to later when project maturity warrants it

## User-Rejected Approaches
- **Users install askr via brew install BippinShekar/askr/askr (full namespace)** — "so now people have to do brew install BippinShekar/askr/askr who does that shit? can't I just make it like brew install askr?" (domain: Formula/askr.rb, Homebrew distribution)

## Files In Play
- `Formula/askr.rb`

## Relational Files
- `askr_state/implementation_bippin.jsonl` (logs): Session decisions and release milestones logged here
- `askr_state/decisions.jsonl` (logs): Architectural decisions recorded here
- `README.md` (documents): Needs update to reflect Phase 3 and 3.5 completion status
- `roadmap.md` (documents): Already updated to reflect Phase 3.5 and Phase 4 status
- `askr/hooks/permission_gate.py` (implements): Permission gate logic for dangerous session detection
- `askr/session/session_start.py` (implements): Task holding logic when dangerous permissions detected
- `askr/extensions/cursor/extension.js` (needs_update): guard_warning notification type not in whitelist; blocks Phase 3.5 IDE popups

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
- `.claude/`

## Blockers
- guard_warning notification type not wired into Cursor extension.js type whitelist — Phase 3.5 IDE popups do not render despite being marked complete
