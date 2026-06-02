# Phase 1  - Dual Forecast Engine
#
# Tracks two independent burn rates:
#
#   Context forecast:
#     - Fill rate per turn from JSONL token growth
#     - Compaction threshold ETA (~90% remaining)
#
#   Quota forecast:
#     - Tokens/minute from JSONL cumulative usage
#     - 5-hour window exhaustion ETA
#     - Exact reset timestamp = first JSONL entry timestamp + 5h
#
# Output: whichever limit fires first → trigger type + ETA
