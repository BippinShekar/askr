# Phase 1 — Session Lifecycle Engine
#
# Handles two distinct resume paths:
#
#   Trigger A (context near compaction ~90%):
#     - Stop current claude process cleanly
#     - Start new session immediately (no wait)
#     - SessionStart hook loads handover.md automatically
#
#   Trigger B (quota running low):
#     - Stop current claude process cleanly
#     - Calculate exact reset time: first JSONL entry timestamp + 5h
#     - Sleep until reset
#     - Start new session
#     - SessionStart hook loads handover.md automatically
