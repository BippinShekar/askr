# Decisions

Append-only. One line per decision. Never edit existing lines.

Format: [YYYY-MM-DD HH:MM] [developer] Decision text. Reason: reason text.

[2026-06-13 21:33] [bippin] Chose to handle both dict and str goal formats in checkpoint.py rather than enforcing a single type. Reason: Provides backward compatibility with existing checkpoints while supporting new JSON-serialized format
[2026-06-13 21:33] [bippin] Implemented delta extraction at the hook level (post_tool_use.py) rather than in checkpoint.py. Reason: Separates concerns: hooks capture raw deltas, checkpoint orchestrates persistence
[2026-06-13 21:54] [bippin] Focus on hook payload inspection rather than binary reverse-engineering of compaction algorithm. Reason: Hook payloads are more directly actionable for improving handover; binary strings provide limited actionable insight
[2026-06-13 22:06] [bippin] Did not refactor _turns_remaining() signature or add new parameters; fixed calculation in-place. Reason: Minimal change surface area reduces risk of introducing new bugs; cost_summary already provides all needed data
[2026-06-13 22:06] [bippin] Did not add new cost_summary fields; reused existing context_window. Reason: Field already present and accessible to session_card via cost_summary dict
