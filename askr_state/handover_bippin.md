# Handover: bippin

Last updated: 2026-08-14 22:33

*Source of truth: `handover_bippin.json`*


## Task
Implemented independent quota polling to close the root cause of rate-limit triggers failing to fire, enabling reliable quota-exhaustion detection and same-session auto-resume across all daemon cycles.

## Discussion
The quota-exhaustion trigger (Trigger B) was structurally broken: it only refreshed via PostToolUse hooks, so once the account hit 100%, no more successful tool calls occurred and the stats file froze at whatever it last recorded (often 84%), preventing the trigger from ever firing. This bug recurred across the entire past week. Fixed by adding an independent 60-second poll that hits the live usage API directly, bypassing the frozen stats file and firing the trigger for the affected project even when its own instrumentation is stale. The fix reuses existing dedup logic to prevent double-firing against the per-project path. All 599 tests pass; daemon self-restarts on source changes and is live without manual intervention.

## Accomplishments
- [x] Implemented independent quota polling (_INDEPENDENT_QUOTA_POLL_SECS = 60) that queries live usage API on every daemon cycle, independent of per-project stats file freshness
- [x] Fixed root cause of Trigger B never firing: quota exhaustion now detected even when stats file is frozen at stale value
- [x] Integrated independent poll with existing tolerance-based dedup to prevent double-firing against per-project trigger path
- [x] Verified fix with 599/599 passing tests and pushed to main (commit 688b8f0)
- [x] Confirmed daemon self-restart on source changes; fix is live without manual restart required

## Next Actions
1. Run overnight autonomous orchestrator test and query events.jsonl for dashboard to validate quota-detection and auto-resume flow end-to-end
   *Why: Confirms that independent poll correctly triggers Stage 4 automation (Escape, notification, wait, cont) when real quota exhaustion occurs; provides ground truth for dashboard visualization*
2. Monitor daemon.log across next 7 days for Trigger B fire patterns and quota=100% detection latency to confirm independent poll is working reliably
   *Why: Validates that the 60-second poll cadence is sufficient and that the fix generalizes across different quota-exhaustion scenarios, not just the specific conditions observed this week*
3. Verify that Stage 4 automation (PID→terminal targeting, Escape keystroke, notification, cont message) fires correctly when independent poll detects exhaustion
   *Why: Completes the end-to-end flow; independent poll is only useful if it successfully triggers the downstream automation that resumes the session*

## Decisions
- Use Escape key (\x1b) for quota-reset menu automation, not arrow-navigation or digit-selection — Binary analysis proves Escape and manual 'Stop and wait' selection both call the same code path (der()); Escape is position-independent and sidesteps the risk of menu-order changes via remote feature flags
- Implement quota-reset automation in five stages: (1) instrumentation for detection, (2) PID→terminal bridge, (3) wait for real data, (4) wire automation, (5) safety-net detection — Stages 1, 2, and 5 are buildable today without live events and carry no automation risk; Stage 3 requires real quota-limit data; Stage 4 (the only risky stage) waits for Stage 3 before proceeding
- Hook-payload capture is centralized in askr/utils/hook_capture.py and called from all seven lifecycle hooks immediately after payload construction — Enables structured analysis of session transitions, trigger events, and handover effectiveness; provides ground truth for visualization and debugging without requiring manual log parsing
- PID→vscode.Terminal targeting uses _get_ancestor_pids to walk the process tree and findTerminalByAncestorPids to match Terminal by ancestor PID — Claude Code may spawn multiple terminal instances; ancestor-PID matching is more reliable than terminal title or index-based targeting and survives terminal renames
- Premature-activity detection (_watch_for_premature_activity) monitors for user keystrokes before rate-limit event is confirmed; if detected, sends billing_anomaly_alert with fault-tolerant multi-channel delivery — Safety net prevents accidental keystroke injection if user is actively typing when rate-limit fires; multi-channel alert ensures user is notified even if one channel fails
- _alert_premature_activity uses independent fault-tolerant channels (log, notification, voice) instead of relying on a single _speak call — Voice is the most critical channel for user awareness but is not independently fault-tolerant; wrapping it in try/except and providing fallback channels ensures alert reaches user even if voice fails
- Independent quota poll runs on 60-second cadence (_INDEPENDENT_QUOTA_POLL_SECS), matched to existing QUOTA_NOTIFY_POLL_SECS cadence — Balances responsiveness (within 60s of real exhaustion) against unknown rate-limit constraints on the usage API; 60s is conservative and aligns with existing quota machinery

## Failed Approaches
- Relying solely on PostToolUse hook to refresh quota stats file for trigger detection — Once account is exhausted, no more successful tool calls occur, so stats file freezes at stale value and trigger never fires; this is a structural gap that recurs every time quota is hit
- Attempting to fix quota-detection without independent polling, only patching the per-project trigger path — Per-project path can only read its own stats file; if that file is frozen, the trigger has no way to learn the truth about real account exhaustion

## Files In Play
- `askr/cli/askr.py`
- `askr_state/decisions.jsonl`

## Relational Files
- `askr/daemon/quota_monitor.py` (imports): Contains independent polling logic and Trigger B firing; central to quota-exhaustion detection
- `askr/daemon/rate_limit_resume.py` (imported_by): Receives Trigger B signal from quota_monitor and executes Stage 4 automation (Escape, notification, wait, cont)
- `askr/utils/hook_capture.py` (configures): Captures hook payloads for all seven lifecycle hooks; provides ground truth for session transition analysis
- `tests/test_quota_monitor.py` (tested_by): 599 tests pass; validates independent poll logic and dedup behavior
