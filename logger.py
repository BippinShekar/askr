import os
import json
import time
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".askr_log")

# Cost per 1M tokens (input/output) — approximate as of 2025
COST_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gpt-4o-mini":               {"input": 0.15, "output": 0.60},
}


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
    if not os.path.exists(LOG_PATH):
        print("No usage logged yet.")
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
        print("No usage logged yet.")
        return

    week_ago = time.time() - 7 * 86400
    recent = [
        e for e in entries
        if time.mktime(time.strptime(e["ts"], "%Y-%m-%d %H:%M")) > week_ago
    ]

    total_cost = sum(e["cost_usd"] for e in recent)
    total_in = sum(e["in"] for e in recent)
    total_out = sum(e["out"] for e in recent)

    print(f"\n{'─'*44}")
    print(f"  askr — last 7 days ({len(recent)} queries)")
    print(f"{'─'*44}")
    print(f"  tokens in:   {total_in:,}")
    print(f"  tokens out:  {total_out:,}")
    print(f"  total cost:  ${total_cost:.4f}")
    print(f"{'─'*44}")

    mode_counts = {}
    for e in recent:
        mode_counts[e["mode"]] = mode_counts.get(e["mode"], 0) + 1
    for m, count in sorted(mode_counts.items(), key=lambda x: -x[1]):
        print(f"  {m:<12} {count} queries")

    print(f"{'─'*44}")
    print(f"\n  last 5 queries:")
    for e in entries[-5:]:
        print(f"  [{e['ts']}] {e['mode']:<8} ${e['cost_usd']:.5f}  {e['q']}")
    print()
