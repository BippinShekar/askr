Last updated: 2026-06-15 13:03

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with an LLM, persisting state across runs and supporting multi-client integrations. It bridges user intent to code changes by orchestrating LLM requests, file operations, test execution, and session handovers—enabling autonomous or semi-autonomous coding workflows.

## What's In Flight

- Discord webhook initialization bug: local .env vars ignored when global ~/.config/askr/.env exists. Fix complete in env.py (load both files with override=False) and askr.py (check send_message return value). Awaiting test verification in staging.
- Context checkpoint card display: verify 'turns remaining' calculation displays correctly after recent cost_summary refactoring.
- Handover system architectural redesign: current checkpoint timing creates stale goals in autonomous sessions. Root cause identified as missing stop checkpoint handler invocation; goal inference must defer to session-end validation rather than mid-session auto-inference.

## Key Decisions Made

- Checkpoint goal format: handle both dict and str formats for backward compatibility rather than enforcing single type.
- Delta extraction at hook level (post_tool_use.py) rather than checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Checkpoint and launch_mode.json are primary handover state carriers; git d