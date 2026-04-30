# askr

A fast, low-token, context-aware AI CLI over your local codebase.

Not a chatbot. Not a wrapper.

A context-aware reasoning layer over your codebase with enforced efficiency and structured outputs.

---

## CORE PRINCIPLES

- Separate thinking (askr) from execution (Claude Code / Cursor)
- Enforce structured, minimal outputs — no fluff
- Always ground responses in repo context
- Combine LLM intelligence with system signals (git, graph, files)
- Keep latency low and UX frictionless (global CLI + hotkey)

---

## USAGE

```bash
ask "cto: what's the best approach to add auth?"
ask "ceo: should we build or buy the payment layer?"
ask "debug: login keeps returning 401"
ask "how does the snapshot system work?"
ask snap
```

No flags. Prefix your query with the mode or skip it — askr figures it out.

---

## MODES

| Mode | Output |
|---|---|
| `cto:` | DECISION / APPROACH / TRADEOFF |
| `ceo:` | DECISION / WHY / NEXT STEP |
| `debug:` | FIX + REASON |
| `sales:` | PITCH / ANGLE / HOOK |
| `deep:` | clear explanation, no fluff |
| *(none)* | 1–2 line answer |

---

## ARCHITECTURE

```
User Input (ask "cto: ...")
→ Mode parsed from prefix (or auto-classified)
→ Snapshot freshness check
→ Context gathered:
    README / CLAUDE.md
    Snapshot summaries (ranked by importance)
    Dependency graph
    Git diff (for debug mode)
→ LLM call (Claude default / OpenAI fallback)
→ Compressed output
```

---

## PROJECT STRUCTURE

```
askr/
├── ask.py              # CLI entry point
├── main.py             # core pipeline
├── config.py           # global config
├── modes.py            # output mode definitions
├── classifier.py       # intent classifier (fallback)
├── snapshot.py         # codebase snapshot builder
├── graph.py            # AST dependency graph
├── git_utils.py        # git diff + commit utilities
├── context_loader.py   # loads README + snapshot
├── client_claude.py    # Anthropic API client
├── client_openai.py    # OpenAI API client
├── utils.py            # compression + helpers
├── requirements.txt
├── install.sh          # global CLI install
└── .llm_snapshot/
    ├── summary.json    # file summaries (LLM-generated)
    ├── graph.json      # dependency graph
    └── meta.json       # last commit + timestamp
```

---

## SETUP

```bash
git clone https://github.com/BippinShekar/askr.git
cd askr
pip install -r requirements.txt
cp .env.example .env   # add your keys
bash install.sh        # makes 'ask' available globally
```

---

## ITERM2 HOTKEY SETUP

1. Open iTerm2 → Preferences → Profiles → create profile `askr`
2. Set command: `ask`
3. Keys → Configure Hotkey Window → bind `Cmd+B`
4. Enable "Floating window" + "Open as hotkey window"

Now `Cmd+B` from anywhere drops a terminal where you just type your query.

---

## SNAPSHOT SYSTEM

Snapshots are auto-built on first run and refreshed when:
- The git commit hash changes
- More than 24 hours have passed

Manual rebuild:
```bash
ask snap
```

---

## FILE IMPORTANCE SCORING

```
Final Score =
    0.5 × LLM importance_score
  + 0.2 × graph centrality (incoming edges)
  + 0.2 × git change frequency
  + 0.1 × entry-point boost
```

Top-ranked files (3–6) are injected into context per query.

---

## COST TRACKING

Every query is logged to `.askr_log` with token count and estimated cost. Run `ask log` to see your weekly summary.

---

## LIMITATIONS

- Graph is static (not true runtime tracing)
- Snapshot quality depends on LLM summaries
- No function-level tracing yet
- No semantic embedding search (yet)

---

## FUTURE

- Streaming output + clipboard integration
- Function-level dependency graph
- LLM summary caching
- Vector retrieval layer
- Runtime instrumentation tracing
