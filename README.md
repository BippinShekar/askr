# askr

A fast, low-token, context-aware AI CLI over your local codebase.

Not a chatbot. Not a wrapper.

Type a question from any project directory and get a structured answer grounded in your actual code — in under 3 seconds.

---

## SETUP

**1. Clone and install**

```bash
git clone https://github.com/BippinShekar/askr.git
cd askr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Add your API keys**

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

Get keys at [console.anthropic.com](https://console.anthropic.com) and [platform.openai.com](https://platform.openai.com).

**3. Make `ask` available globally**

```bash
bash install.sh
source ~/.zshrc   # or restart your terminal
```

Now `ask` works from any directory.

---

## USING IN A PROJECT

Go to any project and run this once:

```bash
cd ~/your-project
ask init
```

This indexes your codebase (estimates cost upfront, adds askr files to your `.gitignore`). After that, just ask:

```bash
ask "cto: best way to structure the auth layer?"
ask "ceo: should we build this feature or buy?"
ask "debug: getting a 401 on every login attempt"
ask "how does the payment flow work?"
```

Responses are auto-copied to your clipboard. Every Q&A is saved to `.askr_history` in your project directory.

---

## MODES

Prefix your query with a mode or skip it — no flags needed.

| Prefix | Output format |
|---|---|
| `cto:` | DECISION / APPROACH / TRADEOFF |
| `ceo:` | DECISION / WHY / NEXT STEP |
| `debug:` | FIX + REASON (includes recent git diff) |
| `sales:` | PITCH / ANGLE / HOOK |
| `deep:` | clear explanation, no fluff |
| `quick:` | 1–2 line answer, no structure |
| *(none)* | defaults to `cto` format |

---

## COMMANDS

```bash
ask "cto: ..."     # ask a question (any mode prefix)
ask init           # index a new project (run once per project)
ask snap           # force full snapshot rebuild
ask log            # show this week's usage + cost
```

---

## ITERM2 HOTKEY (optional)

Set up a floating terminal that opens with `Cmd+B` from anywhere:

1. iTerm2 → Preferences → Profiles → `+` → name it `askr`
2. Under **General** → Command → set to `/bin/zsh`
3. Under **Keys** → Configure Hotkey Window → check "Floating window"
4. Assign hotkey `Cmd+B`

Now `Cmd+B` drops a terminal in your current directory. Type your query, get your answer, close it.

---

## HOW IT WORKS

```
ask "cto: ..."
→ mode parsed from prefix
→ snapshot freshness checked (auto-refreshes on new commits)
→ context loaded:
    README / CLAUDE.md (first 1000 chars)
    top-ranked file summaries (scored by importance + git frequency)
    recent git diff (debug mode only)
→ Claude Haiku call (300 token cap)
→ answer compressed, copied to clipboard, saved to .askr_history
```

The snapshot is incremental — only files changed since the last git commit get re-summarized. First run on a new project does a full index.

---

## COST

Using Claude Haiku (~$0.80/1M input tokens). Typical query: **~$0.001**. A full day of heavy use is under $0.10.

Daily budget cap is set to `$1.00` in `config.py`. Adjust it there.

Track your usage anytime:

```bash
ask log
```

---

## PROJECT STRUCTURE

```
askr/
├── ask.py              # CLI entry point (init / snap / log / query)
├── main.py             # core pipeline
├── config.py           # model, token limits, daily budget
├── modes.py            # output format per mode
├── snapshot.py         # incremental codebase indexer
├── graph.py            # AST dependency graph
├── git_utils.py        # git diff utilities
├── context_loader.py   # loads README + ranked snapshot
├── client_claude.py    # Anthropic SDK client
├── client_openai.py    # OpenAI client (fallback)
├── logger.py           # usage + cost tracking
├── utils.py            # output compression
├── install.sh          # global CLI installer
└── .env.example        # API key template
```

---

## LIMITATIONS

- Snapshot quality depends on LLM file summaries (Claude Haiku)
- Graph is static AST, not runtime
- macOS only for clipboard (`pbcopy`) — Linux users can swap in `xclip`
- No function-level tracing yet

---

## FUTURE

- Brew tap for one-line install (`brew install askr`)
- Web search in debug mode (for errors with no local context)
- Per-project config file (`.askr` override for model, budget, modes)
