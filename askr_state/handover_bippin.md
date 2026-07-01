# Handover: bippin

Last updated: 2026-07-02 01:36

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, extended cross-repo boundary checks to Bash tool calls, documented real Homebrew installation paths in README.md, rebased parallel work from another agent session, and added 64 new tests for guard_runner.py and pre_tool_use.py achieving 122/122 passing tests.

## Discussion
Askr has progressed through four major phases: Phase 3 (notifications), Phase 3.5 (permission guard), and Phase 4 (approval workflow) are fully implemented, tested, and documented. The v0.1.0 release cycle was completed with correct tarball sha256, fixed Homebrew formula, and homebrew-askr tap verification. This session rebased and merged parallel work from another agent branch, updated README.md to document real Homebrew install commands (one-liner `brew install BippinShekar/askr/askr` and tap-then-install form with explanation of why bare `brew install askr` requires homebrew-core merge), merged Bash-boundary guard extension work, and integrated comprehensive test coverage for guard subsystem (64 new tests). All 122 tests pass. Two known gaps remain: guard_warning notification type (non-blocking guard warnings) is dead code—never invoked from pre_tool_use.py despite being wired into extension.js—and PreCompact emergency handover still routes through hardcoded boilerplate instead of real LLM handover path.

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
- [x] Updated README.md with real Homebrew install commands: one-liner tap-and-install and explanation of homebrew-core notability review requirement
- [x] Rebased and merged parallel work from another agent session cleanly onto main

## Next Actions
1. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint function (trigger_type==emergency branch)
   *Why: Known gap: emergency checkpoints currently use template text instead of invoking actual LLM handover mechanism, reducing handover quality in critical scenarios*
2. Activate guard_warning dead code path: trace why pre_tool_use.py never invokes notification.json with type: guard_warning despite extension.js whitelist support, then either wire it into HOOK_MAP or remove the dead code
   *Why: Known gap: non-blocking guard warnings are wired into extension.js but unreachable from Python guard subsystem, leaving Phase 3.5 IDE popup feature incomplete*
3. Audit all remaining test coverage gaps in apply agent, browser automation, and PDF generation subsystems
   *Why: Guard subsystem now has 122/122 passing tests; other core modules may have lower coverage and should be brought to parity*

## Decisions
- Homebrew formula will not be submitted to homebrew-core; instead, users install via tap: brew install BippinShekar/askr/askr — homebrew-core requires notability review and GitHub stars; tap provides immediate distribution without gatekeeping while maintaining professional installation UX
- README.md documents both one-liner and tap-then-install forms with explanation of why bare brew install askr does not work — Transparency about Homebrew's notability requirement prevents user confusion and sets realistic expectations for installation friction

## User-Rejected Approaches
- **Post on social media about Homebrew support shipping and brew install being available** — "nobody knows I am building yet, and that tweet makes it look like I am ready to launch and enable brew install" (domain: external communication / marketing)

## Files In Play
- `README.md`

## Relational Files
- `guard_runner.py` (tested_by): 64 new tests added this session; cross-repo boundary checks extended to Bash tool calls
- `pre_tool_use.py` (tested_by): 64 new tests added this session; guard_warning dead code path identified but not yet activated
- `checkpoint.py` (configures): Emergency handover path (trigger_type==emergency) uses hardcoded boilerplate instead of real LLM handover; identified as next priority
- `extension.js` (imported_by): Whitelists guard_warning notification type but pre_tool_use.py never invokes it; dead code path
