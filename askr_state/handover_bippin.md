# Handover: bippin

Last updated: 2026-07-02 01:33

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, extended cross-repo boundary checks to Bash tool calls, documented real Homebrew installation paths (one-liner and tap-then-install) in the main Install section of README.md, and rebased parallel work from another agent session.

## Discussion
Askr has progressed through four major phases: Phase 3 (notifications), Phase 3.5 (permission guard), and Phase 4 (approval workflow) are fully implemented, tested, and documented. The v0.1.0 release cycle was completed with correct tarball sha256, fixed Homebrew formula, and homebrew-askr tap verification. This session rebased and merged parallel work from another agent branch, updating README.md to document the real Homebrew install commands (one-liner `brew install BippinShekar/askr/askr` and tap-then-install form) with a note explaining why bare `brew install askr` doesn't work without homebrew-core inclusion. All 58 tests pass. Two known gaps remain: guard_warning notification type (non-blocking guard warnings) is dead code—never invoked from pre_tool_use.py despite being wired into extension.js—and PreCompact emergency handover still routes through hardcoded boilerplate instead of real LLM handover path.

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
- [x] Extended cross-repo boundary checks to Bash tool calls in guard_runner.py
- [x] Documented real Homebrew installation paths in README.md main Install section (one-liner and tap-then-install form with explanation of homebrew-core requirement)
- [x] Rebased and merged parallel work from another agent session onto main branch

## Next Actions
1. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint function (trigger_type==emergency branch)
   *Why: Emergency handover currently uses static text instead of invoking the real LLM handover mechanism; this is a known architectural gap blocking proper session continuity*
2. Activate guard_warning dead code path: trace why non-blocking guard warnings from guard_runner.py are never invoked from pre_tool_use.py despite being wired into extension.js, and either invoke them or remove the dead code
   *Why: Phase 3.5's IDE popup for non-blocking guard warnings cannot fire today; either the notification path needs to be triggered or the wiring needs to be removed to reduce confusion*

## Decisions
- Homebrew installation documented via homebrew-askr tap (BippinShekar/askr/askr) rather than homebrew-core merge — homebrew-core inclusion requires notability review and stars; tap-based installation is immediately available and documented with one-liner and tap-then-install forms in README
- Task approval workflow holds queued tasks instead of auto-injecting when dangerous permissions detected — Prevents silent task injection in unrestricted sessions; user must explicitly approve dangerous tasks via IDE notification popup
- Cross-repo boundary checks extended to Bash tool calls in guard_runner.py — Prevents Bash commands from escaping repository boundaries, closing a security gap in the permission gate system

## User-Rejected Approaches
- **Post about brew install support and Homebrew tap availability** — "nobody knows I am building yet, and that tweet makes it look like I am ready to launch; skip it" (domain: README.md, public communication)

## Files In Play
- `README.md`

## Relational Files
- `permission_gate.py` (imported_by): Core security gate detecting dangerous permissions; imported by session_start.py
- `session_start.py` (imports): Holds queued tasks when dangerous permissions detected; calls permission_gate.py
- `guard_runner.py` (configures): Extended with cross-repo boundary checks for Bash tool calls; wires guard_warning notification type
- `extension.js` (configures): Cursor IDE extension; renders task_approval_pending and guard_warning notification popups
- `checkpoint.py` (configures): PreCompact emergency handover still uses hardcoded boilerplate instead of real LLM path (known gap)

## Uncommitted Files
- `.claude/`
