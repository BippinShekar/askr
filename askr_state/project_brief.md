Last updated: 2026-06-13 23:11

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with Claude, handling context persistence, multi-turn workflows, and autonomous session handover. It solves the problem of Claude's context window limits forcing developers to manually restart conversations and lose session state—askr maintains continuity across sessions and intelligently manages token budgets.

## What's In Flight

- Handover system redesign: fixing stale checkpoint creation that prevents autonomous session continuation. Root cause identified as missing stop checkpoint handler invocation, not timing issues.
- Goal inference refactoring: deferring goal inference to session-end validation rather than mid-session auto-inference, which was causing objectives to become out of sync with actual progress.
- Context checkpoint card display: verifying that 'turns remaining' calculation displays correctly in staging before pushing fixes to main.
- Twitter/X launch strategy: curating follow list of 15-20 AI/dev tooling builders, drafting authentic engagement plan (2-3 thread replies daily for 1 week pre-launch), and positioning askr as knowledgeable voice before public reveal in ~1 week.

## Key Decisions Made

- Checkpoint format handles both dict and str goal formats for backward compatibility with existing sessions while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post_tool_use.py) rather than