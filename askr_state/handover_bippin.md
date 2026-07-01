# Handover: bippin

Last updated: 2026-07-02 01:24

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, extended cross-repo boundary checks to Bash tool calls, updated README.md to reflect completion of Phase 3, 3.5, and 4, and documented real Homebrew installation paths (one-liner and tap-then-install) in the main Install section.

## Discussion
Askr has progressed through four major phases: Phase 3 (notifications), Phase 3.5 (permission guard), and Phase 4 (approval workflow) are fully implemented, tested, and documented. The v0.1.0 release cycle was completed with correct tarball sha256, fixed Homebrew formula, and homebrew-askr tap verification. This session merged two parallel agent branches (Bash-boundary hardening and README documentation), verified all 58 tests pass, and identified one remaining gap: guard_warning notification type (non-blocking guard warnings) is dead code—never invoked from pre_tool_use.py despite being wired into extension.js, making Phase 3.5's IDE popup for non-blocking warnings unreachable today. This session added practical Homebrew install documentation clarifying that bare `brew install askr` requires homebrew-core inclusion (not realistic for new projects), so users must either use the one-liner tap command or manually add the tap then install.

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
- [x] Extended pre_tool_use.py cross-repo boundary check to cover Bash tool calls, not just Write/Edit/MultiEdit
- [x] Updated README.md Phase 3 (notifications) and Phase 3.5 (guard) from 'Coming Next' to completed status
- [x] Documented real Homebrew installation paths in README.md Install section: one-liner tap command and tap-then-install two-liner
- [x] Clarified in README that bare 'brew install askr' requires homebrew-core inclusion (not realistic for new projects)

## Next Actions
1. Implement guard_warning invocation path in pre_tool_use.py: add logic to detect non-blocking guard conditions (e.g., cross-repo boundary warnings that do not block execution) and emit guard_warning notification type instead of guard_blocked
   *Why: guard_warning notification type is currently dead code—wired into extension.js but never invoked from pre_tool_use.py. Phase 3.5's IDE popup for non-blocking warnings cannot fire today. This closes the gap between the notification infrastructure and the guard logic.*
2. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint (trigger_type==emergency branch)
   *Why: Emergency handovers currently use static boilerplate instead of dynamically generating a proper state document via the LLM handover pipeline, reducing context fidelity for recovery sessions.*
3. Review and test the complete approval workflow end-to-end: user receives task_approval_pending popup in IDE, approves/rejects task, session resumes with queued task or discards it
   *Why: Phase 4 (approval workflow) is marked complete but no explicit end-to-end test exists confirming the full user interaction loop works in practice.*

## Decisions
- Homebrew installation for askr requires tap-based distribution (homebrew-askr tap) rather than homebrew-core inclusion — homebrew-core requires PR review and notability bar (real usage/stars); not realistic for fresh personal projects. Tap-based distribution is the standard path for new CLIs.
- Document both one-liner (brew tap + install in one command) and two-liner (tap then install) installation paths in README.md Install section — User feedback indicated confusion about why bare 'brew install askr' does not work. Documenting both real paths clarifies the actual installation process and sets correct expectations.

## Files In Play
- `README.md`

## Relational Files
- `pre_tool_use.py` (imports): Contains the guard logic that should invoke guard_warning notification type for non-blocking warnings; currently only invokes guard_blocked
- `extension.js` (configures): Wired to render task_approval_pending and guard_warning notification types; guard_warning path is unreachable due to missing invocation in pre_tool_use.py
- `guard_runner.py` (imported_by): Contains guard_warning notification.json path that is dead code; never invoked from pre_tool_use.py despite being wired into extension.js

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
- `.claude/`
