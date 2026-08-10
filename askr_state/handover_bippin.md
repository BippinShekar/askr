# Handover: bippin

Last updated: 2026-08-11 00:15

*Source of truth: `handover_bippin.json`*


## Task
Built and tested a four-stage companion session handover pipeline with liveness-based lifecycle detection, scratch aggregation, response threading, and compose-box capture; fixed a stale-handover bug in direction inference and wired _start_claude() through direction verification; added hook-payload capture instrumentation across all six lifecycle hooks to enable structured event logging and debugging of session transitions.

## Discussion
The project now has a complete handover mechanism enabling seamless context carry-over when Claude Code spawns new sessions due to exhaustion. Prior sessions built all four stages (lifecycle, scratch merge, response threading, compose-box capture) and fixed critical bugs in direction inference and launch-path verification. This session added instrumentation to capture hook payloads (SessionStart, Stop, PreToolUse, PostToolUse, PreCompact, Notification, UserPromptSubmit) into a centralized hook_capture utility, enabling structured analysis of session transitions and trigger events. The overnight autonomous orchestrator test is ready to run. The user has clarified the quota-reset UX: when the limit hits, a prompt appears with two options (wait for reset / upgrade to Max); the user selects wait, and once reset actually happens, the same session should auto-type 'cont' to resume in-flight work. This requires detection of the reset moment and the exact keystroke sequence to select 'wait for reset' — the latter is a blocker because wrong keystrokes could accidentally trigger a billing action.

## Accomplishments
- [x] Added hook-payload capture instrumentation to all six lifecycle hooks (SessionStart, Stop, PreToolUse, PostToolUse, PreCompact, Notification, UserPromptSubmit) via new askr/utils/hook_capture.py utility
- [x] Created capture_hook_payload() function to centralize hook event logging for structured analysis of session transitions and trigger events
- [x] Wired hook-capture calls into each lifecycle hook immediately after payload construction, before any conditional logic, to ensure all events are recorded
- [x] Created unit tests for hook_capture.py in tests/test_hook_capture.py to validate payload serialization and file I/O
- [x] Updated askr_state/decisions.jsonl with decision to require user-provided keystroke sequence before implementing quota-reset auto-type

## Next Actions
1. Commit hook-capture instrumentation: add all modified hook files (notification.py, post_tool_use.py, pre_compact.py, pre_tool_use.py, session_start.py, stop.py, user_prompt_submit.py), new hook_capture.py utility, test_hook_capture.py, and updated decisions.jsonl in a single clean commit with message 'feat(hooks): add centralized payload capture instrumentation for session transition analysis'
   *Why: Instrumentation is complete and tested; committing enables the overnight autonomous orchestrator test to collect structured event data for visualization and debugging*
2. Run overnight autonomous orchestrator test: plug into power, run caffeinate, seed goals.jsonl with at least one goal, confirm daemon is running via launchd (askr launch), then let it run unattended overnight
   *Why: Four-stage handover pipeline is complete and bug-fixed; hook instrumentation is now in place; overnight run will validate the entire system under realistic autonomous conditions and generate structured event log data for visualization*
3. After overnight run completes, query askr_state/events.jsonl to build visualization dashboard showing session tree, context/quota savings across sessions, trigger type distribution, and multi-session persistence story
   *Why: Structured event log is now being written by hook-capture instrumentation; visualization will prove the handover mechanism is working and quantify the benefit*
4. Monitor compose-box capture for false positives or missed carries during the overnight run; if the parser misses valid input or captures noise, refine extractPendingInput() logic in extension.js and re-test
   *Why: Best-effort capture is live but untested at scale; overnight run will expose edge cases*
5. BLOCKER: Get exact keystroke sequence to select 'wait for reset' option in the quota-limit prompt (e.g., arrow key + Enter, number + Enter, Tab + Enter, etc.) — do not proceed with auto-typing until this is confirmed
   *Why: Wrong keystroke injection could accidentally trigger plan upgrade (real billing action); need user-provided ground truth before building this*
6. Once keystroke sequence is confirmed, implement quota-reset detection and auto-type 'cont' in the same session instead of opening a fresh companion; wire this into the post-reset relaunch path in lifecycle.py
   *Why: User clarified the desired UX: resume in-flight work in the same session after reset, not spawn a new one*
7. If overnight run succeeds, document the four-stage companion handover feature in CLAUDE.md and add it to the project README as a core capability of the autonomous orchestrator
   *Why: Feature is complete and tested; documentation will make it discoverable and maintainable*

## Decisions
- Do not implement auto-typing into terminal on quota reset until exact keystroke sequence is provided by user — Risk of accidental plan upgrade (real billing action) if keystroke guess is wrong; requires ground-truth confirmation before any automation
- Stale-handover detection in _infer_direction() checks for real (non-askr) commits between candidate handover and HEAD; if any exist, falls through to Signal 4 instead of trusting stale next_actions — A session can finish real work, commit it, and end without crossing a trigger threshold — its checkpoint never fires, so canonical handover stays stale. This check prevents wasting tokens re-verifying already-resolved issues
- _start_claude() (idle/goal-autolaunch path) must call _infer_direction() like all other launch paths — It was the only launch path that skipped direction inference entirely and unconditionally executed next_actions without verification; this caused token waste on autonomous relaunches
- Hook-payload capture is centralized in askr/utils/hook_capture.py and called from all six lifecycle hooks immediately after payload construction — Enables structured analysis of session transitions, trigger events, and handover effectiveness; provides ground truth for visualization and debugging without requiring manual log parsing

## User-Rejected Approaches
- **Auto-type 'cont' into terminal on a timer when quota reset happens, without user confirmation or idle-state gating** — "User flagged this as infringement on user control earlier in conversation; now clarified that auto-type should happen but only after reset actually occurs, and only if the user has already selected 'wait for reset' in the prompt" (domain: askr/session/lifecycle.py, quota-reset relaunch path)

## Files In Play
- `askr/hooks/notification.py`
- `askr/hooks/post_tool_use.py`
- `askr/hooks/pre_compact.py`
- `askr/hooks/pre_tool_use.py`
- `askr/hooks/session_start.py`
- `askr/hooks/stop.py`
- `askr/hooks/user_prompt_submit.py`
- `askr/utils/hook_capture.py`
- `tests/test_hook_capture.py`

## Relational Files
- `askr/orchestrator/infer_direction.py` (imported_by): Core direction-inference logic; prior session fixed Signal 3 (stale-handover detection) and wired _start_claude() to call it; hook instrumentation now provides event data to validate direction inference quality
- `askr_state/events.jsonl` (written_by): Structured event log for session lineage and trigger tracking; hook-capture instrumentation now feeds into this; will be queried after overnight run for visualization
- `askr/session/lifecycle.py` (configures): Session lifecycle management; hook-capture instrumentation provides visibility into lifecycle transitions and will enable quota-reset detection and auto-type implementation

## Uncommitted Files
- `askr/hooks/notification.py`
- `askr/hooks/post_tool_use.py`
- `askr/hooks/pre_compact.py`
- `askr/hooks/pre_tool_use.py`
- `askr/hooks/session_start.py`
- `askr/hooks/stop.py`
- `askr/hooks/user_prompt_submit.py`
- `askr_state/decisions.jsonl`
- `askr_state/failed_approaches.md`
- `askr_state/implementation_bippin.jsonl`
- `askr/utils/hook_capture.py`
- `tests/test_hook_capture.py`

## Blockers
- BLOCKER: Exact keystroke sequence to select 'wait for reset' in quota-limit prompt is unknown; cannot implement auto-type without user confirmation to avoid accidental plan upgrade
