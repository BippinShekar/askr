# Failed Approaches

Cumulative cross-session log. Never overwritten — append only.

- [2026-06-12] Assumed stats file path construction was wrong — verified it matches Claude Code's actual dash-replacement format, so path logic is not the issue
- [2026-06-12] Debugging the hook's JSONL path construction — path logic was confirmed working; the real problem was missing venv/dependencies, not path resolution.
- [2026-06-12] Asking the user to manually run debug commands on the friend's machine — user correctly rejected this as unsustainable; the fix must be in `install.sh` itself.
- [2026-06-12] None — analysis phase incomplete, no approaches were tested or rejected.
- [2026-06-13] Reusing standard handover template for emergency checkpoints — loses critical mid-operation context
- [2026-06-13] Storing only transcript entries in emergency handover — does not capture execution state of current operation
- [2026-06-13] Reusing standard handover template for emergency checkpoints — loses critical mid-operation context and execution state
- [2026-06-13] Storing only transcript entries in emergency handover — does not capture execution state of current operation or what was interrupted
- [2026-06-13] Markdown-based handover format — lacks type safety and structured parsing for recovery logic
- [2026-06-13] Using Haiku to infer last_known_line from transcript text — unreliable for line number accuracy
- [2026-06-13] Relying on consensus alone for phase 3.12 validation — needed documented evidence (GitHub issue)
- [2026-06-13] Searching Claude binary (strings) for auto-compact logic and context percentage calculations — Yielded limited actionable results; binary strings are fragmented and lack context. Hook implementation inspection is more direct.
- [2026-06-13] Grepping for turns_remaining, context_pct, context_remaining patterns across filesystem — No matches found; these patterns may not exist in codebase or use different naming conventions
- [2026-06-13] Attempting to infer handover state from git diff and implementation_state.md alone — User's question revealed this misses the autonomous session continuation mechanism entirely; checkpoint files are the actual state carriers
- [2026-06-13] Assuming handover files are written after all session actions complete. — User's analysis revealed handover is persisted mid-session before tool execution hooks finish, causing stale content.
- [2026-06-13] Auto-inferring session goals from user messages without end-of-session validation. — Goals become stale and misaligned with actual session progress by the time next autonomous session reads them.
