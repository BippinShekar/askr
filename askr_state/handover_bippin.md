# Handover: bippin

Last updated: 2026-06-09 00:05

# Handover Document

## Task
Refine YC application answers about past technical projects by removing marketing language, correcting technical details, and ensuring answers are concise and human-sounding rather than resume-like.

## Status
Three project answers being refined for YC application:

1. **Askr (Open source)** — FINAL: "I was building multiple projects simultaneously and Claude Code kept losing context mid-task. Askr watches the session, checkpoints before Claude degrades, commits structured project state to git, and resumes automatically. Building it for myself, while using it every day."

2. **AI Audit Engine** — FINAL: Correction made — uses Google Calendar directly for booking, NOT Calendly. Pipeline confirmed: Apollo → Serper → Claude → Gmail → Google Calendar → Razorpay. Queue-based execution via BullMQ on schedule. Remove emphasis formatting (em dashes).

3. **Heuretos (heuretos.com)** — For "most impressive thing" question: Answer currently reads as architecture description rather than achievement. User mentioned NotebookLM was in original paste but transcript does not show that mention — clarification needed on whether NotebookLM should be included.

## Failed Approaches
- Calendly integration — user cannot afford subscription, switched to Google Calendar API instead.
- Marketing-style language
