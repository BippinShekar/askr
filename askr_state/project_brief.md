Last updated: 2026-06-13 21:54

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across invocations and supporting multi-client integration. It wraps LLM interactions (Claude, OpenAI, etc.) in a session model with hooks, state recovery, and IDE integration so developers can hand off coding tasks to AI and resume them later without losing context.

## What's In Flight

- Investigating Claude Code session handover system gaps: examining how context compaction works, what metadata is available in pre/post-compaction hooks, and what state can be reliably recovered across sessions. Currently 35% complete; focus is on extracting hook payload structure and building tabular analysis of handover capabilities vs. gaps.
- Backward compatibility for checkpoint state: recently implemented dual support for dict and string goal formats to avoid breaking existing persisted sessions while supporting new JSON-serialized format.
- Delta extraction at hook level: moved responsibility for capturing raw state deltas from checkpoint orchestration to post_tool_use.py hooks to separate concerns.

## Key Decisions Made

- Handle both dict and string goal formats in checkpoint.py rather than enforcing a single type. Provides backward compatibility with existing checkpoints while supporting new serialization format.
- Implement delta extraction at the hook level (post_tool_use.py) rather than in checkpoint.py. Separ