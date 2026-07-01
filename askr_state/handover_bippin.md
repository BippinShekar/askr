# Handover: bippin

Last updated: 2026-07-01 22:59

*Source of truth: `handover_bippin.json`*


## Task
askr is a multi-agent session management system for Claude Code; this session fixed companion session opening to wait for Stop hook completion before firing, preventing mid-reply context loss when quota threshold triggers new session.

## Discussion
User reported that companion session opening was firing mid-reply when crossing 60% quota threshold, causing context loss and requiring manual pinning. Root cause was lifecycle.py watching for stats file deletion (which never happens between turns) instead of waiting for Stop hook's authoritative completion signal. This session fixed the detection mechanism to properly synchronize session handoff with reply completion, ensuring new window opens after Claude's message finishes rather than interrupting it.

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
- [x] Fixed 8 hallucination and boundary issues in guard system: cross-repo boundary validation, retry state tracking, guard rule tightening, and decision.jsonl pollution prevention
- [x] Fixed companion session opening to wait for Stop hook completion signal instead of watching for stats file deletion

## In Progress
- `None`: Architectural design for stateful retry mechanism that captures failure context (screenshots, error reasoning) to enable learning-based job resubmission instead of blind retry

## Next Actions
1. Implement stateful retry mechanism that captures failure context (screenshots, error reasoning, form state) before deferring spam-flagged or failed jobs to end-of-session queue
   *Why: User proposed enriching failed job retry logic with contextual information to enable learning-based retry instead of blind resubmission; this is the next architectural enhancement after fixing queue orchestration*
2. Test companion session handoff at 60% quota threshold to verify new window opens after reply completes without context loss
   *Why: Lifecycle fix was just committed; needs validation that the Stop hook signal properly synchronizes session transfer*
3. Monitor guard system for false positives after tightening rules; verify that legitimate operations are no longer blocked by inferred constraints
   *Why: Guard system was over-blocking based on absence of mention; recent fixes should eliminate hallucination loops but need validation in live operation*

## Decisions
- Absence of a file/directory/pattern in architecture.md does NOT mean it is prohibited; only explicit forbiddance in CLAUDE.md or architecture.md triggers guard blocks — Guard was over-blocking legitimate operations based on absence of mention; explicit prohibition is required to block
- Cross-repo boundary checks must be enforced in pre_tool_use.py to prevent tool use outside the askr repository — Multi-agent system must be confined to its own codebase to prevent unintended modifications to external projects
- Retry state must preserve original operation type (read/write/create) across retries to avoid false 'creating new file' labels — Retries on existing files were being mislabeled as creates, causing false guard blocks on legitimate retry operations
- Guard-inferred signals (phrases like 'do NOT write this to decisions.jsonl') must be filtered before writing to decisions.jsonl — Prevents guard rationale from polluting the architectural decision record and creating false constraints in future sessions
- Companion session opening must wait for Stop hook to signal completion before firing, not watch for file deletion — Prevents mid-reply session switches that cause context loss and force manual pinning; Stop hook is the authoritative completion signal

## Failed Approaches
- Assuming the stats file anomaly was caused by session_start.py being called twice with different cwd values — Investigation revealed the root cause was cwd drift during the session (via Bash `cd` command) combined with find_project_root() stopping at the first .claude it found, not multiple session_start.py calls
- Treating all decisions.jsonl entries equally in guard context without distinguishing guard-inferred from developer-approved decisions — Created self-reinforcing hallucination loop where guard blocks became hard constraints, causing false positives and blocking legitimate work
- Using absence of mention in architecture as a blocking signal — Caused guard to invent constraints and block legitimate patterns that were simply not documented
- Watching for stats file deletion to detect Stop hook completion in lifecycle.py — Stop hook does not delete the stats file; this was a false assumption that caused companion sessions to fire mid-reply

## Files In Play
- `askr/session/lifecycle.py`
- `askr/hooks/pre_tool_use.py`
- `askr/hooks/stop.py`
- `askr/session/checkpoint.py`
- `askr/session/guard.py`

## Relational Files
- `askr/hooks/stop.py` (imported_by): Stop hook is the authoritative signal for session completion; lifecycle.py now waits for this signal before opening companion session
- `askr/hooks/pre_tool_use.py` (configures): Guard system that validates tool use; recent fixes tightened rules to prevent false blocks from inferred constraints
- `askr/session/checkpoint.py` (imported_by): Checkpoint system filters guard-inferred phrases before writing decisions.jsonl to prevent pollution of architectural record
