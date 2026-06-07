Last updated: 2026-06-07 07:26

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git so developers can resume work seamlessly. It solves the problem of losing progress and context when Claude Code hits limits mid-session. The companion `ask` CLI provides natural language Q&A against project context. Together they enable long-running development workflows without manual handoffs.

## What's In Flight

- Phase 1 context-switching validation: auto-summarization and context trigger thresholds are implemented but not stress-tested under real quota pressure.
- Token-savings visualization: building PNG reports (via matplotlib + Discord webhook multipart upload) to show compression savings and time gains per session.
- Morning report delivery to Discord: status unknown—need to confirm screenshot delivery is working.
- Phase 4 decision pending: determine whether to proceed with advanced features or first validate Phase 1 functionality and complete visualization pipeline.

## Key Decisions Made

- `askr` handles only subcommands (`goal`, `status`, `goals`, etc.); natural language queries route through `ask` CLI instead. This separation keeps session orchestration focused.
- State persistence uses git commits for handoffs between developers and sessions; all context lives in append-only decision logs and state files.
- Visualization approach: generate enriched PNG graphs