# Handover: bippin

Last updated: 2026-07-01 23:59

*Source of truth: `handover_bippin.json`*


## Task
askr is a multi-agent session management system for Claude Code; prior sessions fixed handover document generation, guard system boundary validation, and companion session lifecycle. This session discovered a critical security vulnerability (live Discord webhook in public GitHub history) and initiated a comprehensive launch-readiness audit to identify all blockers before public release.

## Discussion
Previous sessions resolved cross-repo contamination, guard hallucination, and session handoff synchronization. This session pivoted to launch readiness after user expressed public commitment to release askr via brew install within one week. A critical finding emerged: the public GitHub repository contains a plaintext Discord webhook URL in committed history (commit 50eba93 on origin/main), requiring immediate remediation via git history rewrite. User requested a comprehensive audit of all launch blockers including test coverage, dependencies, documentation, deployment readiness, and TODO/FIXME markers before public announcement.

## Accomplishments
- [x] Fixed 8 hallucination and boundary issues in guard system: cross-repo boundary validation, retry state tracking, guard rule tightening, and decision.jsonl pollution prevention
- [x] Fixed companion session opening to wait for Stop hook completion signal instead of watching for stats file deletion
- [x] Fixed handover document generation to scope file paths to askr repository only, preventing cross-repo contamination in project state
- [x] Discovered critical security vulnerability: live Discord webhook URL exposed in plaintext in public GitHub repository history (commit 50eba93, origin/main)
- [x] Initiated comprehensive launch-readiness audit: scanned codebase for TODO/FIXME/XXX markers, hardcoded paths, test coverage gaps, dependency declarations, and deployment script validation

## In Progress
- `None`: Launch-readiness audit results pending: background agents running verification of unbuilt safety gates, race conditions, test suite validation, and deployment readiness assessment. Audit completion awaited.

## Next Actions
1. URGENT: Rotate Discord webhook URL immediately. Remove plaintext webhook from git history using git-filter-branch or BFG Repo-Cleaner, force-push to origin/main, and regenerate webhook in Discord settings.
   *Why: Live webhook URL is publicly exposed in GitHub history; any actor can post to askr's Discord channel. This is a critical security vulnerability blocking public release.*
2. Await completion of background launch-readiness audit agents and review findings: identify all TODO/FIXME/XXX markers, hardcoded paths, test coverage gaps, missing documentation, deployment script validation, and dependency lock files. Produce prioritized blockers list.
   *Why: User committed to public release (brew install) and is telling people it will be live in a week. Audit must identify all gaps before announcement.*
3. Validate test suite passes end-to-end: confirm pytest runs cleanly, all imports resolve, no hardcoded /Users/bippin paths remain, and critical paths (session init, handoff, guard system) are covered.
   *Why: Public release requires confidence that core functionality is tested, reproducible, and portable across machines.*
4. Review and finalize Homebrew formula (Formula/*.rb): ensure all dependencies are declared, installation paths are correct, post-install hooks work on macOS, and no hardcoded user paths exist.
   *Why: User's public commitment is 'brew install askr'; formula must be production-ready and work for any user.*
5. Test companion session handoff at 60% quota threshold to verify new window opens after reply completes without context loss
   *Why: Lifecycle fix was committed in prior session; needs end-to-end validation before public release.*
6. Scan entire codebase for hardcoded /Users/bippin paths and replace with environment-aware or relative paths
   *Why: Brew installation will fail or behave incorrectly if any hardcoded user paths remain in source or config.*

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- CRITICAL: Live Discord webhook URL exposed in public GitHub history (commit 50eba93, origin/main) — must be removed via git history rewrite before public release
- Launch-readiness audit results pending — awaiting background agent completion to identify all remaining blockers
- Unknown: potential hardcoded /Users/bippin paths in codebase that will break brew installation
- Unknown: test coverage gaps and deployment script readiness — audit in progress
