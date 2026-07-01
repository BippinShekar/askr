# Handover: bippin

Last updated: 2026-07-02 01:32

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, extended cross-repo boundary checks to Bash tool calls, and documented real Homebrew installation paths (one-liner and tap-then-install) in the main Install section of README.md.

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
- [x] Documented real Homebrew installation paths in README.md (one-liner tap command and tap-then-install form)
- [x] Rebased and merged parallel agent branch work on README documentation with Bash-boundary hardening commits

## Next Actions
1. Implement guard_warning invocation path in pre_tool_use.py to fire non-blocking guard warnings (type: guard_warning) for permission violations that do not require blocking, enabling Phase 3.5's IDE popup for non-blocking warnings
   *Why: guard_warning notification type is wired into extension.js but dead code—never invoked from pre_tool_use.py, making non-blocking guard warnings unreachable today*
2. Fix PreCompact emergency handover in checkpoint.py (create_checkpoint function, trigger_type==emergency branch) to route through real LLM handover path instead of hardcoded boilerplate
   *Why: Emergency handovers currently bypass the proper LLM handover mechanism, reducing context quality and consistency*

## Decisions
- Homebrew installation requires users to either run one-liner `brew install BippinShekar/askr/askr` or manually add tap then install; bare `brew install askr` is not documented as viable path — Bare `brew install askr` requires homebrew-core inclusion, which is not realistic for new projects; documented paths reflect actual working installation methods

## User-Rejected Approaches
- **Post about Homebrew support going live with engagement language (e.g., 'brew tap now live 🎉')** — "brother nobody knows I am building yet, and that tweet makes it look like I am ready to launch and enable brew install" (domain: X platform engagement strategy)

## Files In Play
- `README.md`

## Relational Files
- `pre_tool_use.py` (imports): Contains HOOK_MAP and guard invocation logic; guard_warning type needs to be invoked here
- `guard_runner.py` (imported_by): Implements guard_warning notification path that is currently dead code
- `extension.js` (configures): Whitelist for guard_warning notification type is already in place; waiting for pre_tool_use.py to invoke it
- `checkpoint.py` (configures): Contains create_checkpoint function with hardcoded emergency handover boilerplate that needs real LLM path

## Uncommitted Files
- `.claude/`
