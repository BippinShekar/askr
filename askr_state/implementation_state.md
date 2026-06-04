# Implementation State

Each developer owns their section.

<!-- section:bippin -->
## bippin

Last active: 2026-06-04 21:07

### In Progress

- [21:18] Modified: /Users/bippin/Desktop/askr/askr/cli/askr.py
- [21:18] Modified: /Users/bippin/Desktop/askr/askr/session/lifecycle.py
- [21:17] Ran: grep -rn "this chat\|context_pct\|context_tokens\|104\|207" /Users/bippin/Deskto
- [21:17] Ran: ls /Users/bippin/.cursor/extensions/ | grep -i claude
- [21:17] Ran: grep -n "context\|104\|session_stats\|this chat" /Users/bippin/Desktop/askr/ask.
- [21:16] Ran: pgrep -fl claude 2>/dev/null | head -20
- [21:16] Ran: grep -n "session_stats\|context_pct\|context_tokens\|session_id\|updated_at" /Us
- [21:16] Ran: pgrep -f claude -l 2>/dev/null | head -20
- [21:15] Ran: grep -n "pgrep\|kill\|claude\|SIGTERM\|SIGKILL" /Users/bippin/Desktop/askr/askr/
- [21:15] Ran: cat ~/.config/askr/session_stats.json 2>/dev/null || echo "not found"
- [21:15] Ran: ps aux | grep -E "(askr|stigerm|caffeinate|python)" | grep -v grep
[nothing - session not started]

### Completed

- ./ask.py - Serve as the executable entry point for the askr CLI application
- ./askr/cli/ask.py - Command-line interface for askr - an AI-powered code question-answering system that analyzes project codebases using Claude and OpenAI APIs
- ./askr/hooks/pre_compact.py - Emergency fallback mechanism that creates a checkpoint before Claude auto-compacts context, preserving work state when the forecast engine misses the 90% context threshold
- ./askr/utils/config.py - Central configuration file for an LLM-based code assistant system
- ./askr/session/forecast.py - Track and predict two independent token burn rates to determine which usage limit will be exceeded first
- ./askr/session/monitor.py - Monitor token usage and remaining capacity across two data sources to provide real-time burn rate data for forecasting
- ./askr/session/checkpoint.py - Manages state persistence and handover between execution sessions by creating checkpoints, updating state files, and coordinating with lifecycle management
- ./askr/session/lifecycle.py - Manages session resumption and continuity across Claude process restarts using two distinct trigger mechanisms based on context usage and quota status
- ./askr/session/safe_pause.py - Determines whether it is safe to interrupt and checkpoint by monitoring system state before pausing operations
- ./askr/clients/claude.py - Provides interface for interacting with Anthropic Claude API models with support for standard and web-enabled queries
- ./askr/clients/openai.py - Manages OpenAI API client initialization and chat completion requests for the askr application
- ./Formula/askr.rb - Homebrew formula for installing Askr, a context-aware codebase Q&A tool accessible from the terminal
- ./askr/state/reader.py - Load and aggregate developer context information from state files to build a comprehensive context injection for AI assistants
- ./askr/state/writer.py - Manage persistent state files for developer handovers, task tracking, decisions, and implementation progress
- ./askr/hooks/stop.py - Claude Code Hook that executes when a code session ends. Generates handover documentation from session transcript, commits state changes, and pushes to repository.
- ./askr/hooks/session_start.py - Initialize Claude Code sessions by pulling latest git state and injecting project context
- ./askr/qa/context_loader.py - Load and manage project context information from files and snapshots for AI assistant integration
- ./askr/utils/display.py - Provides terminal UI components and formatting functions for the askr application using the Rich library
- ./askr/qa/graph.py - Extract and analyze import dependencies across multiple programming languages, building dependency graphs
- ./askr/qa/modes.py - Define response formatting templates for different communication contexts and audience types
- ./askr/utils/env.py - Load environment variables and API keys from multiple fallback locations in priority order
- ./askr/utils/logger.py - Track and manage API usage costs for language models with daily budget enforcement
- ./askr/state/config.py - Configuration and state management for the askr application
- ./askr/cli/askr.py - Manage Claude AI hook installation and configuration for the askr application
- ./askr/hooks/user_prompt_submit.py - Pre-processing hook that intercepts user messages before Claude processes them, extracting and storing the active objective/task

### Files Owned

[not assigned yet]
<!-- /section:bippin -->
