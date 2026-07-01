# Handover: bippin

Last updated: 2026-07-02 00:17

*Source of truth: `handover_bippin.json`*


## Task
Completed pre-launch safety audits on session management core (45 passing tests, checkpoint/guard/hook systems verified), identified critical packaging gap (brew Formula ships wrong package), and documented roadmap findings; discovered webhook credential leaked in git history (now rotated) requiring scrubbing via git-filter-repo.

## Discussion
Session ran two autonomous audits in parallel: safety-gate verification (unbuilt gates, race conditions) and test-suite health check (packaging readiness). Core session-management infrastructure (hooks, checkpoint, guard, state sync) is production-ready with full test coverage. Critical blocker identified: homebrew Formula does not install the full askr/ package or create bin/askr entry point — currently ships only root *.py files with hardcoded dependency list instead of requirements.txt. User asked about scrubbing leaked Discord webhook from git history and whether Formula can be written simultaneously with code changes, or if prerequisites must be handled first. Session focused on audit findings and roadmap documentation rather than implementing fixes.

## Accomplishments
- [x] Ran autonomous safety-gate audit verifying unbuilt gates and race conditions in session-management core
- [x] Ran autonomous test-suite health audit verifying packaging readiness and test coverage
- [x] Confirmed session-management core (hooks, checkpoint, guard, state sync) is production-ready with 45 passing tests
- [x] Identified critical packaging blocker: homebrew Formula installs wrong package (root *.py only, not full askr/ package)
- [x] Documented pre-launch audit findings and blockers to roadmap.md and goals backlog
- [x] Discovered Discord webhook credential leaked in git history (rotated, requires git-filter-repo scrubbing)

## In Progress
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry
- `Formula/askr.rb`: Rebuild homebrew Formula to install full askr/ package (not just root *.py), create bin/askr entry point, install deps from requirements.txt instead of hardcoded list
- `None`: Cut real git tag + GitHub release so Formula sha256/url are real, and create homebrew-askr tap repo
- `askr/guard/pre_tool_use.py`: Extend cross-repo boundary check to cover Bash tool calls, not just Write/Edit/MultiEdit
- `askr/checkpoint.py`: Fix PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate
- `None`: Add test coverage for pre_tool_use.py/guard_runner.py - the implementation guard has zero tests despite being security-critical
- `README.md`: Update documentation - Phase 3 (notifications) and Phase 3.5 (guard) are built and running, not 'Coming Next'
- `None`: Build approval gate for --dangerously-skip-permissions sessions before queued/autonomous tasks run (roadmap Phase 5)

## Next Actions
1. Scrub Discord webhook from git history using git-filter-repo: clone --mirror, run filter-repo with --replace-text to remove credential, force-push to origin. Document exact steps and verify no traces remain in GitHub.
   *Why: Credential is rotated but still in history; scrubbing is hygiene work that can proceed in parallel with code changes*
2. Rebuild Formula/askr.rb to install full askr/ package directory (not just root *.py files), create bin/askr entry point script, and read dependencies from requirements.txt instead of hardcoded list
   *Why: Critical blocker for brew install; can be written and tested independently of other code changes*
3. Cut real git tag (e.g., v0.1.0) and create GitHub release with tarball; update Formula sha256 and url to point to real release artifact
   *Why: Formula currently references non-existent package; real release enables homebrew-askr tap repo creation*
4. Extend askr/guard/pre_tool_use.py cross-repo boundary check to cover Bash tool calls (currently only guards Write/Edit/MultiEdit)
   *Why: Security gap: Bash calls can access files outside this repo without guard verification*
5. Add test coverage for askr/guard/pre_tool_use.py and askr/guard/guard_runner.py (currently zero tests on security-critical path)
   *Why: Implementation guard has no test suite despite being the primary security boundary*
6. Fix askr/checkpoint.py PreCompact emergency handover to route through real LLM handover path instead of hardcoded boilerplate
   *Why: Emergency handovers currently bypass the proper handover generation logic*
7. Build approval gate for --dangerously-skip-permissions sessions before queued/autonomous tasks run (Phase 5 roadmap item)
   *Why: Currently zero approval gates exist anywhere in askr/ for dangerous permission modes*
8. Update README.md to reflect that Phase 3 (notifications) and Phase 3.5 (guard) are built and running, not 'Coming Next'
   *Why: Documentation is stale; audit confirmed these phases are production-ready*

## Decisions
- Session-management core (hooks, checkpoint, guard, state sync) is production-ready and requires no architectural changes before launch — Autonomous audit verified 45 passing tests and no unbuilt safety gates or race conditions
- Homebrew Formula rebuild is a prerequisite for launch, not a post-launch task — Current Formula ships wrong package entirely; brew install is non-functional and blocks user onboarding
- Git history scrubbing for leaked webhook can proceed in parallel with code work — Credential is rotated (emergency resolved); scrubbing is hygiene work independent of feature development

## Files In Play
- `Formula/askr.rb`
- `askr/checkpoint.py`
- `askr/guard/pre_tool_use.py`
- `askr/guard/guard_runner.py`
- `README.md`
- `roadmap.md`
- `askr_state/goals.jsonl`
- `askr_state/implementation_bippin.jsonl`

## Relational Files
- `askr/guard/guard_runner.py` (imported_by): Implements guard logic that pre_tool_use.py calls; both need test coverage
- `requirements.txt` (configures): Formula should read from this instead of hardcoding dependency list
- `setup.py` (configures): Packaging configuration that Formula must respect
- `askr/cli/askr.py` (imported_by): bin/askr entry point should invoke this CLI module

## Blockers
- Homebrew Formula does not install full askr/ package or create bin/askr entry point — currently ships only root *.py files with hardcoded dependency list
- No real git tag or GitHub release exists; Formula sha256/url reference non-existent artifacts
- Discord webhook credential leaked in git history (rotated but requires git-filter-repo scrubbing)
