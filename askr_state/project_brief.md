Last updated: 2026-06-08 03:33

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining a rolling window of recent conversation history and persisting decisions, progress, and code changes. The core problem: Claude Code sessions hit limits unpredictably, losing context and forcing manual recovery. Askr makes this invisible.

## What's In Flight

- Rolling window implementation complete: last 5 exchanges injected into prompt context via `_load_recent_history` in `askr/qa/pipeline.py`. Eliminates need for in-memory tokenization since askr is a stateless CLI tool (fresh process per invocation).
- Installation and functionality verification in co-founder's separate repository. Testing that rolling window context injection works correctly in new environment before declaring ready for shared use.
- Quota impact measurement: compaction burns 4-5% of quota window silently over ~4 minutes. Askr now prevents compaction by maintaining rolling context window.

## Key Decisions Made

- Rolling window approach (last 5 exchanges) chosen over in-memory tokenization/retrieval. Reason: askr is stateless CLI tool where each invocation is a fresh process, making persistent memory impossible and slower than rolling window