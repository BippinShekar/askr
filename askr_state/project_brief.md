Last updated: 2026-06-07 08:10

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without losing context or repeating work.

## What's In Flight

- Phase 3.7: Rich visual Discord reports showing token savings and context compression metrics per session. Generates PNG visualization with matplotlib showing session timeline, token cost delta (with/without askr), money saved, and time saved. Wires into morning report webhook as file attachment.
- Context trigger testing: validating that users naturally hit 75% context limit on small sessions; currently blocked by auto chat window switch pre-context summarization working too well.
- State persistence layer: `askr/state/` modules (reader, writer, config) managing task/decision/progress file updates across session boundaries.

## Key Decisions Made

- Visualization approach: generate PNG directly with matplotlib and send via Discord webhook multipart upload, delete temp file after send. Rejected screenshot-based approach as lower impact.
- Architecture: modular split between session lifecycle (monitor, forecast, checkpoint, safe_pause), Claude Code hooks (session_start, user_prompt_submit, stop, pre_compact), persistent state layer,