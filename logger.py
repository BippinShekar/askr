import os
import json
import time
from datetime import datetime, date

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".askr_log")

COST_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 1.00,  "output":  5.00},
    "claude-sonnet-4-6":         {"input": 3.00,  "output": 15.00},
    "gpt-5.4-nano-2026-03-17":   {"input": 0.20,  "output":  1.25},
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
    from display import console
    spent = _today_spend()
    if spent >= daily_limit:
        console.print(f"\n  [bold red]✗ daily budget hit[/bold red] [dim](${spent:.4f} / ${daily_limit:.2f})[/dim]")
        console.print("  [dim]run[/dim] [bold]ask log[/bold] [dim]to review. resets tomorrow.[/dim]\n")
        raise SystemExit(1)
    remaining = daily_limit - spent
    if remaining < daily_limit * 0.2:
        console.print(f"  [yellow]⚠ budget low:[/yellow] [dim]${spent:.4f} spent today, ${remaining:.4f} left[/dim]")


def log_query(model, input_tokens, output_tokens, mode, query_preview):
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

    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return cost


def show_summary():
    from display import console, print_summary

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

    total_cost = sum(e["cost_usd"] for e in recent)
    total_in = sum(e["in"] for e in recent)
    total_out = sum(e["out"] for e in recent)

    mode_counts = {}
    for e in recent:
        mode_counts[e["mode"]] = mode_counts.get(e["mode"], 0) + 1

    print_summary(recent, entries, total_in, total_out, total_cost, mode_counts)
