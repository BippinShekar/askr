# Failed Approaches

Cumulative cross-session log. Never overwritten — append only.

- [2026-06-12] Assumed stats file path construction was wrong — verified it matches Claude Code's actual dash-replacement format, so path logic is not the issue
- [2026-06-12] Debugging the hook's JSONL path construction — path logic was confirmed working; the real problem was missing venv/dependencies, not path resolution.
- [2026-06-12] Asking the user to manually run debug commands on the friend's machine — user correctly rejected this as unsustainable; the fix must be in `install.sh` itself.
- [2026-06-12] None — analysis phase incomplete, no approaches were tested or rejected.
