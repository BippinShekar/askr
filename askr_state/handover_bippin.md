# Handover: bippin

Last updated: 2026-07-01 23:58

*Source of truth: `handover_bippin.json`*


## Task
askr is a multi-agent session management system for Claude Code; prior sessions fixed handover document generation, guard system boundary validation, and companion session lifecycle. This session discovered a critical security vulnerability (live Discord webhook in public GitHub history) and initiated a launch-readiness audit to identify all blockers before public release.

## Discussion
Previous sessions resolved cross-repo contamination, guard hallucination, and session handoff synchronization. This session pivoted to launch readiness after user expressed commitment to public availability (brew install target). A critical finding emerged: the public GitHub repository contains a plaintext Discord webhook URL in committed history (commit 50eba93 on origin/main), requiring immediate remediation. User requested a comprehensive audit of all launch blockers, test coverage, dependencies, and deployment readiness before public announcement.

## Accomplishments
- [x] Fixed 8 hallucination and boundary issues in guard system: cross-repo boundary validation, retry state tracking, guard rule tightening, and decision.jsonl pollution prevention
- [x] Fixed companion session opening to wait for Stop hook completion signal instead of watching for stats file deletion
- [x] Fixed handover document generation to scope file paths to askr repository only, preventing cross-repo contamination in project state
- [x] Discovered critical security vulnerability: live Discord webhook URL exposed in plaintext in public GitHub repository history (commit 50eba93, origin/main)
- [x] Initiated comprehensive launch-readiness audit: identified need to assess test coverage, dependencies, documentation, deployment scripts, and all TODO/FIXME markers

## In Progress
- `None`: Launch-readiness audit in progress: running test suite validation, TODO/FIXME/XXX marker inventory, dependency verification, and deployment readiness assessment. Audit results pending.

## Next Actions
1. URGENT: Rotate Discord webhook URL immediately. Remove plaintext webhook from git history using git-filter-branch or BFG Repo-Cleaner, force-push to origin/main, and regenerate webhook in Discord settings.
   *Why: Live webhook URL is publicly exposed in GitHub history; any actor can post to askr's Discord channel. This is a critical security vulnerability blocking public release.*
2. Complete launch-readiness audit: review all TODO/FIXME/XXX markers, test coverage gaps, missing documentation, deployment script validation, and dependency lock files. Produce prioritized blockers list.
   *Why: User committed to public release (brew install) and is telling people it will be live in a week. Audit must identify all gaps before announcement.*
3. Validate test suite passes end-to-end: confirm pytest runs cleanly, all imports resolve, and critical paths (session init, handoff, guard system) are covered.
   *Why: Public release requires confidence that core functionality is tested and reproducible.*
4. Review and finalize Homebrew formula (Formula/*.rb): ensure all dependencies are declared, installation paths are correct, and post-install hooks work on macOS.
   *Why: User's public commitment is 'brew install askr'; formula must be production-ready.*
5. Test companion session handoff at 60% quota threshold to verify new window opens after reply completes without context loss
   *Why: Lifecycle fix was committed in prior session; needs validation that the Stop hook signal properly synchronizes session transfer.*
6. Monitor guard system for false positives after tightening rules; verify that legitimate operations are no longer blocked by inferred constraints
   *Why: Guard system was over-blocking based on absence of mention; recent fixes should eliminate hallucination loops but need validation in live operation.*

## Decisions
- Absence of a file/directory/pattern in architecture.md does NOT mean it is prohibited; only explicit forbiddance in CLAUDE.md or architecture.md triggers guard blocks — Guard was over-blocking legitimate operations based on absence of mention; explicit prohibition is required to block
- Cross-repo boundary checks must be enforced in pre_tool_use.py to prevent tool use outside the askr repository — Multi-agent system must be confined to its own codebase to prevent unintended modifications to external projects
- Retry state must preserve original operation type (read/write/create) across retries to avoid false 'creating' classifications — Guard system was misclassifying retried operations; operation type must be immutable across retry boundaries
- Public GitHub repository requires all secrets (Discord webhooks, API keys, tokens) to be rotated and removed from history before launch — Plaintext secrets in public git history are permanently compromised; rotation and history rewrite are mandatory for security

## Relational Files
- `askr/session/checkpoint.py` (configures): Handover document generation; prior session fixed scoping to askr repo only
- `askr/guard/pre_tool_use.py` (configures): Cross-repo boundary enforcement; prior session fixed 8 hallucination issues
- `Formula/*.rb` (configures): Homebrew installation formula; critical for public release via brew install
- `requirements.txt` (configures): Python dependencies; must be validated for public release
- `tests/*.py` (tested_by): Test suite validation required before public announcement

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- CRITICAL: Live Discord webhook URL exposed in public GitHub repository history (commit 50eba93, origin/main) — must be rotated and removed from history before any public announcement
- Launch-readiness audit incomplete — full inventory of TODO/FIXME/XXX markers, test coverage gaps, and deployment readiness not yet assessed
- Homebrew formula validation pending — Formula/*.rb must be tested on macOS before public release
