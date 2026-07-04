import os
import json
import time
from datetime import datetime, date

LOG_PATH = os.path.join(os.path.expanduser("~/.config/askr"), "usage.log")
ERROR_LOG_PATH = os.path.join(os.path.expanduser("~/.config/askr"), "error.log")

COST_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 1.00,  "output":  5.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "gpt-4o-mini":               {"input": 0.15,  "output":  0.60},
}


def _today_spend():
    if not os.path.exists(LOG_PATH):
        return 0.0
    today = date.today().strftime("%Y-%m-%d")
    total = 0.0
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "").startswith(today):
                    total += entry.get("cost_usd", 0)
            except Exception:
                pass
    return total


def check_budget(daily_limit):
    from askr.utils.display import console
    spent = _today_spend()
    if spent >= daily_limit:
        console.print(f"\n  [bold red]✗ daily budget hit[/bold red] [dim](${spent:.4f} / ${daily_limit:.2f})[/dim]")
        console.print("  [dim]run[/dim] [bold]ask log[/bold] [dim]to review. resets tomorrow.[/dim]\n")
        raise SystemExit(1)
    remaining = daily_limit - spent
    if remaining < daily_limit * 0.2:
        console.print(f"  [yellow]⚠ budget low:[/yellow] [dim]${spent:.4f} spent today, ${remaining:.4f} left[/dim]")


def log_query(model, input_tokens, output_tokens, mode, query_preview):
    """Logs a real, metered API-key call (askr/qa/pipeline.py's \`ask\` command
    only) — cost_usd here reflects an actual charge against ANTHROPIC_API_KEY."""
    rates = COST_TABLE.get(model, {"input": 1.0, "output": 5.0})
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000

    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": model,
        "mode": mode,
        "in": input_tokens,
        "out": output_tokens,
        "cost_usd": round(cost, 6),
        "q": query_preview[:60],
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return cost


def log_oauth_query(model, input_tokens, output_tokens, mode, query_preview):
    """Logs an OAuth-authenticated call (Claude Code's own subscription —
    every internal askr LLM call except \`ask <query>\`). There's no per-token
    price here since nothing is billed directly; a fabricated cost_usd would
    be misleading. Instead records the account's real five_hour/seven_day
    quota utilization (askr/session/usage_api.get_quota_status(), the same
    endpoint behind Claude Code's own /usage command) sampled right after this
    call, so quota burn is tracked against ground truth, not invented dollars."""
    quota_five_hour = None
    quota_seven_day = None
    try:
        from askr.session.usage_api import get_quota_status
        status = get_quota_status()
        if status:
            quota_five_hour = status.five_hour_pct
            quota_seven_day = status.seven_day_pct
    except Exception:
        pass

    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": model,
        "mode": mode,
        "in": input_tokens,
        "out": output_tokens,
        "quota_five_hour_pct": quota_five_hour,
        "quota_seven_day_pct": quota_seven_day,
        "q": query_preview[:60],
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_error(component: str, detail: str):
    """Append a one-line error record for a swallowed exception.

    For failures that are safe to degrade gracefully from (a feature that
    falls back to [] or "" rather than crashing the session) but where
    silence would otherwise leave no trace if something is actually broken
    (e.g. a bad API key making every LLM call fail) — see askr's own
    failed_approaches.md, which cites silent `except: pass` blocks as the
    root cause of several real, hard-to-diagnose bugs.
    """
    try:
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ERROR_LOG_PATH, "a") as f:
            f.write(f"[{ts}] {component}: {detail.strip()[:500]}\n")
    except Exception:
        pass


def log_line_mark() -> int:
    """Return current line count of the log file as a cost measurement baseline."""
    if not os.path.exists(LOG_PATH):
        return 0
    try:
        with open(LOG_PATH) as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def cost_since_mark(mark: int) -> float:
    """Sum cost of all log entries written after line `mark`."""
    if not os.path.exists(LOG_PATH):
        return 0.0
    try:
        with open(LOG_PATH) as f:
            lines = f.readlines()
        total = 0.0
        for line in lines[mark:]:
            line = line.strip()
            if not line:
                continue
            try:
                total += json.loads(line).get("cost_usd", 0.0)
            except Exception:
                pass
        return total
    except Exception:
        return 0.0


def show_summary():
    from askr.utils.display import console, print_summary

    if not os.path.exists(LOG_PATH):
        console.print("\n  [dim]no usage logged yet[/dim]\n")
        return

    entries = []
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

    if not entries:
        console.print("\n  [dim]no usage logged yet[/dim]\n")
        return

    week_ago = time.time() - 7 * 86400
    recent = [
        e for e in entries
        if time.mktime(time.strptime(e["ts"], "%Y-%m-%d %H:%M")) > week_ago
    ]

    api_key_entries = [e for e in recent if "cost_usd" in e]
    oauth_entries    = [e for e in recent if "cost_usd" not in e]

    total_cost = sum(e["cost_usd"] for e in api_key_entries)
    total_in = sum(e["in"] for e in recent)
    total_out = sum(e["out"] for e in recent)

    mode_counts = {}
    for e in recent:
        mode_counts[e["mode"]] = mode_counts.get(e["mode"], 0) + 1

    oauth_summary = None
    if oauth_entries:
        latest = oauth_entries[-1]
        oauth_summary = {
            "queries": len(oauth_entries),
            "tokens_in": sum(e["in"] for e in oauth_entries),
            "tokens_out": sum(e["out"] for e in oauth_entries),
            "latest_five_hour_pct": latest.get("quota_five_hour_pct"),
            "latest_seven_day_pct": latest.get("quota_seven_day_pct"),
        }

    print_summary(recent, entries, total_in, total_out, total_cost, mode_counts, oauth_summary)
