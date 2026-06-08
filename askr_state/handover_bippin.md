# Handover: bippin

Last updated: 2026-06-09 00:06

# Handover Document

## Task
Evaluate and refine YC application answers for Leaps startup, specifically addressing whether technical depth in project descriptions is sufficient and whether mentioning the same project (Heuretos) across multiple answers damages credibility.

## Status
- User is applying to YC with Leaps startup
- Three projects reviewed: Askr, AI Audit Engine, Heuretos (heuretos.com)
- AI Audit Engine uses Google Calendar for booking (not Calendly) — direct integration with Google Calendar API
- AI Audit Engine pipeline confirmed: Apollo → Serper → Claude → Gmail → Google Calendar → Razorpay, queue-based with BullMQ
- Heuretos architecture: 9 specialized agents, Neo4j DAG orchestration, parallel execution, query rewriter pipeline, containerized Next.js frontend
- Heuretos was deliberately shut down despite working functionality due to non-viable CAC model and closing differentiation window from base model capabilities
- Final decision: Do NOT repeat Heuretos mention across multiple YC application answers — including it in both the "most impressive thing" question and the main Leaps description would damage credibility

## Failed Approaches
- Including NotebookLM mention in Heuretos description — was not in final version
- Repeating Heuretos details
