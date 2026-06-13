Last updated: 2026-06-13 22:06

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It lets developers run AI-assisted coding workflows that maintain context across sessions, track token usage, and integrate with IDEs.

## What's In Flight

- Fixing context growth extrapolation: corrected denominator in _turns_remaining() calculation (100 - baseline_pct instead of 100 - current_pct) and updated checkpoint messaging in report_image.py. 95% complete; awaiting final commit and push.
- Tabular analysis of handover system gaps — examining hook payloads and checkpoint data to identify missing pieces in session continuity.
- Multi-client LLM provider abstraction — clients module is in place but implementation details still being solidified.

## Key Decisions Made

- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.
- Delta extraction happens at the hook level (post_tool_use.py) rather than in checkpoint.py — separates concerns between raw capture and persistence orchestration.
- Focus on hook payload inspection for handover improvements rather than reverse-engineering binary compaction algorithms — payloads are more actionable.
- Fixed _turns_remaining() calculation in-place without refactoring signature