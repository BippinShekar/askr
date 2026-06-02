# Phase 1  - Safe Pause Engine
#
# Before checkpointing, determines whether it is safe to interrupt.
#
# SAFE:   tool idle, no active file writes, tests not running, git clean
# UNSAFE: file write active, tests running, migration/deploy in progress
#
# Watches OS process table and filesystem state  - runs as external daemon,
# not inside Claude hooks.
