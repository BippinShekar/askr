Last updated: 2026-06-06 23:01

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Stage 10: End-to-end testing of project brief generation with real checkpoint workflow
- Verification of test suite status and fixing any failures from last session
- Review of file changes and decisions.md to understand what was completed in the previous session

## Key Decisions Made

- State is persisted to git as the single source of truth for handoffs between developers and sessions
- Session monitoring is split into discrete modules: token forecasting, safe pause detection, checkpoint generation, and resumption orchestration
- Claude Code integration happens via hooks at key lifecycle points (session start, prompt submit, session stop, pre-compact)
- Handover documents are auto-generated on session end to capture task, status, failed approaches, and open questions
- State files store developer context, active objectives, task progress, and decisions in append-only format

## Open Goals

- Test Stage 10 project brief generation end-to-end with real checkpoint
- Verify test status from last Bash output and fix any failures
- Review files changed since last session