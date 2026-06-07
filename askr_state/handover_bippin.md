# Handover: bippin

Last updated: 2026-06-08 03:08

## Task
Implement rolling window context for `ask` CLI tool to replace in-memory tokenization/retrieval, and draft a tweet about Claude's auto-compaction quota burn.

## Status
- `/Users/bippin/Desktop/askr/askr/qa/pipeline.py`: Added `_load_recent_history` function that injects last 5 Q&A exchanges into prompt context on each invocation
- Git commit created: "feat: rolling window of last 5 his" (message truncated in transcript)
- Rolling window approach confirmed as viable — each `ask` invocation is a fresh process, so persistent in-memory storage is not feasible
- Quota analysis completed: auto-compaction burns ~4-5% of 5-hour quota window, takes ~4 minutes, silently drops context
- Tweet draft finalized: "claude's auto-compact is a silent killer. 4 minutes frozen. quota burned. context quietly dropped. i don't know what it forgot. i build on top of this, and boom next few hours or days spending to rectify/salvage what went wrong."

## Failed Approaches
- In-memory tokenization and retrieval: rejected because `ask` is a stateless CLI tool with no persistent process to hold memory between invocations; re-embedding history on every call would be slower than rolling window

##
