# Phase 1 — Checkpoint Engine
#
# On trigger (from forecast.py, confirmed safe by safe_pause.py):
#
#   1. Generate handover.md — complete structured resume file
#   2. Update all state files (decisions, current_task, implementation_state)
#   3. Git commit + push
#   4. Signal lifecycle.py with trigger type:
#        Trigger A (context) → new session immediately
#        Trigger B (quota)   → wait for reset, then resume
