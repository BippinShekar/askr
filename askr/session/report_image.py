"""
Phase 3.7 — Rich Visual Reports

Generates a dark-card PNG summarising a session or daily rollup.
Sent to Discord via send_file(), temp file deleted after upload.

Two image types:
  - session_card(): checkpoint or session-end summary card
  - morning_report_card(): daily rollup across all sessions
"""

from __future__ import annotations
import os
import tempfile
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

_BG      = "#0f1117"
_CARD    = "#1a1d27"
_ACCENT  = "#7289da"   # Discord blurple
_GREEN   = "#43b581"
_YELLOW  = "#faa61a"
_RED     = "#f04747"
_TEXT    = "#dcddde"
_SUBTEXT = "#72767d"
_WHITE   = "#ffffff"


def _fmt_usd(amount: float) -> str:
    if amount < 0.01:
        return f"${amount:.4f}"
    return f"${amount:.2f}"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _fmt_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m" if m else f"{h}h"


# ---------------------------------------------------------------------------
# Session card
# ---------------------------------------------------------------------------

def session_card(
    trigger_type: str,
    developer: str,
    cost_summary: dict,
    duration_seconds: int = 0,
    goals_completed: list[str] | None = None,
    files_changed: list[str] | None = None,
    context_history: list[float] | None = None,
) -> Optional[str]:
    """
    Generate a session summary PNG.

    Returns the temp file path on success, None on failure.
    Caller must delete the file after sending.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.gridspec import GridSpec
    except ImportError:
        return None

    goals_completed = goals_completed or []
    files_changed   = files_changed or []

    has_files    = bool(files_changed)
    has_goals    = bool(goals_completed)
    content_rows = (len(goals_completed[:3]) if has_goals else 0) + (min(len(files_changed), 5) if has_files else 0)
    has_timeline = bool(context_history and len(context_history) >= 3)
    fig_height   = max(7.5 if has_timeline else 6.0, 5.5 + content_rows * 0.25)
    fig, ax_main = plt.subplots(figsize=(10, fig_height))
    fig.patch.set_facecolor(_BG)
    ax_main.set_visible(False)

    if has_timeline:
        gs = GridSpec(2, 1, figure=fig, height_ratios=[2, 1], hspace=0.35,
                      top=0.93, bottom=0.08, left=0.06, right=0.97)
        ax_card = fig.add_subplot(gs[0])
        ax_time = fig.add_subplot(gs[1])
    else:
        gs = GridSpec(1, 1, figure=fig, top=0.93, bottom=0.08, left=0.06, right=0.97)
        ax_card = fig.add_subplot(gs[0])
        ax_time = None

    # ---- card background ----
    for ax in ([ax_card] + ([ax_time] if ax_time else [])):
        ax.set_facecolor(_CARD)
        for spine in ax.spines.values():
            spine.set_edgecolor(_SUBTEXT)
            spine.set_linewidth(0.5)

    # ---- title ----
    label_map = {
        "context":   "Context Checkpoint",
        "quota":     "Quota Checkpoint",
        "stop":      "Session Complete",
        "manual":    "Manual Checkpoint",
        "emergency": "Emergency Checkpoint",
    }
    title = label_map.get(trigger_type, trigger_type.replace("_", " ").title())
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
    fig.text(0.05, 0.97, f"askr — {title}", color=_WHITE, fontsize=14, fontweight="bold", va="top")
    fig.text(0.97, 0.97, f"{developer}  ·  {ts}", color=_SUBTEXT, fontsize=9, va="top", ha="right")

    ax_card.set_xlim(0, 1)
    ax_card.set_ylim(0, 1)
    ax_card.axis("off")

    # ---- stat tiles ----
    tiles = [
        ("Cost", _fmt_usd(cost_summary.get("cost_usd", 0)), _TEXT),
        ("Saved", _fmt_usd(cost_summary.get("savings_usd", 0)), _GREEN),
        ("Tokens", _fmt_tokens(cost_summary.get("context_tokens", 0)), _TEXT),
        ("Context", f"{round(cost_summary.get('context_pct', 0) * 100)}%", _YELLOW),
        ("Turns",   str(cost_summary.get("turns", 0)), _TEXT),
        ("Time",    _fmt_time(duration_seconds), _ACCENT),
    ]
    tile_w = 1.0 / len(tiles)
    for i, (label, value, color) in enumerate(tiles):
        x = (i + 0.5) * tile_w
        ax_card.text(x, 0.72, value, color=color, fontsize=18, fontweight="bold",
                     ha="center", va="center", transform=ax_card.transAxes)
        ax_card.text(x, 0.48, label, color=_SUBTEXT, fontsize=9,
                     ha="center", va="center", transform=ax_card.transAxes)

    # ---- divider ----
    ax_card.axhline(y=0.38, color=_SUBTEXT, linewidth=0.4, xmin=0.02, xmax=0.98)

    # ---- goals / files — split into two columns ----
    col_split = 0.52  # goals on left, files on right

    # Left column: goals
    if goals_completed:
        goal_lines = ["Goals completed"]
        goal_lines += [f"  ✓ {g[:48]}" for g in goals_completed[:4]]
        ax_card.text(0.03, 0.30, "\n".join(goal_lines), color=_GREEN, fontsize=8.5,
                     va="top", transform=ax_card.transAxes, linespacing=1.6,
                     fontfamily="monospace")

    # Right column: files changed
    if files_changed:
        file_lines = ["Files changed"]
        file_lines += [f"  {f[:42]}" for f in files_changed[:5]]
        if len(files_changed) > 5:
            file_lines.append(f"  +{len(files_changed) - 5} more")
        ax_card.text(col_split, 0.30, "\n".join(file_lines), color=_SUBTEXT, fontsize=8.5,
                     va="top", transform=ax_card.transAxes, linespacing=1.6,
                     fontfamily="monospace")

    # ---- timeline ----
    if ax_time and context_history:
        xs = list(range(len(context_history)))
        ys = [c * 100 for c in context_history]

        ax_time.plot(xs, ys, color=_ACCENT, linewidth=1.5, zorder=3)
        ax_time.fill_between(xs, ys, alpha=0.15, color=_ACCENT, zorder=2)

        # trigger fire point (last turn = where checkpoint fired)
        ax_time.axvline(x=xs[-1], color=_YELLOW, linewidth=1, linestyle="--", alpha=0.7)
        ax_time.text(xs[-1] + 0.3, ys[-1] + 2, "trigger", color=_YELLOW,
                     fontsize=7, va="bottom")

        ax_time.axhline(y=75, color=_RED, linewidth=0.6, linestyle=":", alpha=0.6)
        ax_time.text(0.5, 76, "75% checkpoint", color=_RED, fontsize=7, va="bottom")

        ax_time.set_ylim(0, 105)
        ax_time.set_ylabel("context %", color=_SUBTEXT, fontsize=8)
        ax_time.set_xlabel("turn", color=_SUBTEXT, fontsize=8)
        ax_time.tick_params(colors=_SUBTEXT, labelsize=7)
        ax_time.set_facecolor(_CARD)
        ax_time.yaxis.label.set_color(_SUBTEXT)
        ax_time.xaxis.label.set_color(_SUBTEXT)
        for spine in ax_time.spines.values():
            spine.set_edgecolor(_SUBTEXT)
            spine.set_linewidth(0.4)

    # ---- save ----
    fd, path = tempfile.mkstemp(suffix=".png", prefix="askr_session_")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Morning report card
# ---------------------------------------------------------------------------

def morning_report_card(
    date: str,
    sessions: int,
    total_seconds: int,
    total_cost_usd: float,
    total_savings_usd: float,
    total_tokens: int,
    goals_completed: list[str] | None = None,
    goals_open: list[str] | None = None,
) -> Optional[str]:
    """
    Generate a daily rollup PNG.

    Returns temp file path on success, None on failure.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        return None

    goals_completed = goals_completed or []
    goals_open      = goals_open or []

    fig, _ = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(_BG)
    _.set_visible(False)

    gs = GridSpec(1, 1, figure=fig, top=0.92, bottom=0.06, left=0.05, right=0.97)
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(_CARD)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for spine in ax.spines.values():
        spine.set_edgecolor(_SUBTEXT)
        spine.set_linewidth(0.5)

    fig.text(0.05, 0.97, "askr — Morning Report", color=_WHITE, fontsize=14, fontweight="bold", va="top")
    fig.text(0.97, 0.97, date, color=_SUBTEXT, fontsize=9, va="top", ha="right")

    tiles = [
        ("Sessions",   str(sessions), _TEXT),
        ("Time saved", _fmt_time(total_seconds), _ACCENT),
        ("Cost",       _fmt_usd(total_cost_usd), _TEXT),
        ("Saved",      _fmt_usd(total_savings_usd), _GREEN),
        ("Tokens",     _fmt_tokens(total_tokens), _TEXT),
    ]
    tile_w = 1.0 / len(tiles)
    for i, (label, value, color) in enumerate(tiles):
        x = (i + 0.5) * tile_w
        ax.text(x, 0.78, value, color=color, fontsize=20, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes)
        ax.text(x, 0.55, label, color=_SUBTEXT, fontsize=9,
                ha="center", va="center", transform=ax.transAxes)

    ax.axhline(y=0.44, color=_SUBTEXT, linewidth=0.4, xmin=0.02, xmax=0.98)

    y = 0.34
    if goals_completed:
        goal_str = "  ✓ " + "   ✓ ".join(g[:45] for g in goals_completed[:4])
        ax.text(0.03, y, goal_str, color=_GREEN, fontsize=9, va="center", transform=ax.transAxes)
        y -= 0.13

    if goals_open:
        open_str = "  → " + "   → ".join(g[:45] for g in goals_open[:3])
        ax.text(0.03, y, open_str, color=_SUBTEXT, fontsize=9, va="center", transform=ax.transAxes)

    fd, path = tempfile.mkstemp(suffix=".png", prefix="askr_report_")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return path
