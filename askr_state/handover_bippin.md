# Handover: bippin

Last updated: 2026-07-02 01:34

*Source of truth: `handover_bippin.json`*


## Task
Built and deployed a four-stage permission gate system to prevent dangerous task injection in unrestricted sessions, added task approval workflow with notification integration, completed Phase 3.5 security hardening with full test coverage, cut first tagged release (v0.1.0) with Homebrew formula and GitHub release, verified end-to-end installation via homebrew-askr tap, extended cross-repo boundary checks to Bash tool calls, documented real Homebrew installation paths in README.md, rebased parallel work from another agent session, and added 64 new tests for guard_runner.py and pre_tool_use.py achieving 122/122 passing tests.

## Discussion
Askr has progressed through four major phases: Phase 3 (notifications), Phase 3.5 (permission guard), and Phase 4 (approval workflow) are fully implemented, tested, and documented. The v0.1.0 release cycle was completed with correct tarball sha256, fixed Homebrew formula, and homebrew-askr tap verification. This session rebased and merged parallel work from another agent branch, updated README.md to document real Homebrew install commands, merged Bash-boundary guard extension work, and integrated comprehensive test coverage for guard subsystem (64 new tests). All 122 tests pass. Two known gaps remain: guard_warning notification type (non-blocking guard warnings) is dead code—never invoked from pre_tool_use.py despite being wired into extension.js—and PreCompact emergency handover still routes through hardcoded boilerplate instead of real LLM handover path.

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
- [x] Documented real Homebrew installation paths (one-liner and tap-then-install) in README.md Install section
- [x] Rebased and merged parallel work from another agent session onto main branch
- [x] Added 64 new tests for pre_tool_use.py and guard_runner.py guard subsystem coverage
- [x] Achieved 122/122 passing tests in full test suite after guard test integration

## Next Actions
1. Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate in checkpoint.py create_checkpoint function (trigger_type==emergency branch)
   *Why: Known architectural gap: emergency handover currently uses static boilerplate instead of invoking actual LLM handover mechanism, reducing handover quality in critical failure scenarios*
2. Activate guard_warning notification type by invoking it from pre_tool_use.py when non-blocking guard conditions are detected, wiring it through HOOK_MAP and .claude/settings.json to enable IDE popup rendering
   *Why: guard_warning is currently dead code despite being fully wired into extension.js; activating it completes Phase 3.5 non-blocking guard warning feature*
3. Investigate and document the worktree-to-parent-repo absolute path boundary check false positive (navigating from worktree back to its own parent repo via absolute path gets blocked)
   *Why: Rough edge in guard extension: worktree isn't recognized as 'the same project' when accessed via absolute path, causing unnecessary guard blocks in legitimate development workflows*

## Decisions
- Homebrew formula published to homebrew-askr tap instead of homebrew-core — Faster iteration cycle and full control over formula updates without waiting for homebrew-core review process; users install via `brew install BippinShekar/askr/askr` or tap-then-install pattern
- Defer spam-flagged jobs to end of session instead of inline retry — Reduces session complexity and retry loops; allows user to review spam-flagged applications separately after main job batch completes
- Extend guard boundary checks to Bash tool calls in addition to Python imports — Closes security gap where Bash scripts could access files outside project boundary; maintains consistent cross-repo protection across all tool types

## Failed Approaches
- LinkedIn location field: passing full location string directly to combobox field — Full location strings (e.g., 'San Francisco, CA, United States') do not trigger city autocomplete dropdown; requires extraction of city name only
- Ramp spam_warning recovery: inline retry with immediate resubmit — Spam-flagged applications require different handling strategies (overlay banner vs form replacement); deferring to end of session reduces complexity and improves UX

## Files In Play
- `tests/test_pre_tool_use_guard.py`
- `tests/test_guard_runner.py`
- `askr_state/implementation_bippin.jsonl`

## Relational Files
- `askr/guard/pre_tool_use.py` (tested_by): Core guard logic for detecting dangerous permissions and blocking unsafe tool calls; 64 new tests added this session
- `askr/guard/guard_runner.py` (tested_by): Guard execution and cross-repo boundary checking; extended to Bash tool calls; comprehensive test coverage added
- `askr/guard/permission_gate.py` (imported_by): Detects dangerous permissions (skip-permissions, unrestricted Bash, rm in allow list); used by session_start.py to hold queued tasks
- `askr/session_start.py` (imports): Holds queued tasks when dangerous permissions detected; implements task approval workflow
- `.claude/extension.js` (configures): Wired to render task_approval_pending and guard_warning notification types as IDE popups
- `README.md` (documents): Updated with real Homebrew installation commands (one-liner and tap-then-install) and explanation of homebrew-askr tap
- `askr/checkpoint.py` (imports): Contains create_checkpoint function with emergency handover branch that currently uses hardcoded boilerplate instead of real LLM handover

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`
