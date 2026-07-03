# Project Brief

Askr is an AI-assisted development orchestrator that solves three problems Claude developers face: session exhaustion (hitting context/quota mid-task), team knowledge drift (teammates don't see what was built last night), and architectural conflicts (Claude sounds confident but the approach breaks existing code). It runs a background daemon that monitors Claude Code sessions, automatically checkpoints when limits approach, commits project state to git, and resumes in a fresh session with full handover context — so work stops never.

## What's In Flight

Session lifecycle overhaul — fixing broken daemon and cost tracking. Core issue: session orchestration is broken; lifecycle.py's context/quota monitoring and auto-resume aren't firing. Ongoing work: checkpoint.py handover generation, stop.py session-end notifications and voice announcements, test_checkpoint_merge.py (test coverage for merged sessions). Secondary concern: need explicit cost/token tracking and performance metrics to answer "how many tokens are we burning per subprocess call, what latency, and why did this cost spike?"

Shipped but incomplete: Implementation guard blocking path works (pre_tool_use.py validates architecture before writes), but non-blocking warning path (guard_runner.py) is dead code — never wired into IDE or hook pipeline.

## Key Decisions Made

Daemon never kills user's live session — only opens a companion session alongside it, letting user manually switch when ready. Checkpoints are union-merge safe (handover.md, decisions.jsonl, goals.jsonl use append-only timestamps) so two developers can pull git state and always resume from correct ground truth. Session-end voice announcements use a two-voice sonic logo (short "Done." prefix + contextual detail in different voice) to make askr's notifications distinctive from generic OS alerts. Empty audio strings are valid skip signals — simplifies callers. Cost tracking belongs on the hook boundary (each trigger type gets cost recorded), not deep in checkpoint paths. Context percentage is source-of-truth (parsed from JSONL token counts), quota percentage comes from Anthropic /oauth/usage endpoint. Turn-elapsed-time (last human message to now) gates voice pings independent of total session duration (prevents spam on long sessions). Tool results logged in JSONL are filtered out when finding "last real user message" — they're system responses, not human input.

## Open Goals

Fix daemon — context and quota triggers not firing. Implement cost/token tracking and performance metrics API so users can answer "what burned the budget" and understand per-trigger overhead. Wire up non-blocking guard warnings (guard_runner.py) to IDE. Cross-repo Claude Code session switching (upstream doesn't support it yet; askr could address this as a feature).

## How to Get Started

1. Run `python3 -m askr.session.lifecycle` locally to check daemon startup and logs — look for context/quota poll cycle in ~/.config/askr/daemon.log.
2. Check `askr_state/implementation_bippin.jsonl` to see which hooks are actually firing during a session (PostToolUse logs here). Compare against expected lifecycle in README (SessionStart → PostToolUse → Stop).
3. Review the three uncommitted files — stop.py (session-end notifications), checkpoint.py (handover generation), lifecycle.py (daemon polling) — to understand what's been changed and why. Tests in test_checkpoint_merge.py validate checkpoint behavior.
4. Run `pytest tests/test_checkpoint_merge.py -v` to confirm handover/merge logic works in isolation, then start a real Claude Code session and watch daemon.log to find where the lifecycle breaks.
