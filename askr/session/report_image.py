"""
Phase 3.7 — Rich Visual Reports (v2)

Complete redesign. Cards are built around one hero metric that proves
askr's value: developer interruptions avoided, context intercepted, etc.
"""

from __future__ import annotations
import os
import tempfile
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

_BG     = "#0d1117"
_CARD   = "#161b22"
_BORDER = "#21262d"
_GREEN  = "#3fb950"
_PURPLE = "#a371f7"
_AMBER  = "#d29922"
_RED    = "#f85149"
_BLUE   = "#58a6ff"
_TEXT   = "#e6edf3"
_MUTED  = "#8b949e"
_DIM    = "#3d444d"
_WHITE  = "#ffffff"

_ACCENT = {
    "stop":      _GREEN,
    "context":   _PURPLE,
    "quota":     _AMBER,
    "manual":    _BLUE,
    "emergency": _RED,
}

_LABEL = {
    "stop":      "SESSION COMPLETE",
    "context":   "CONTEXT CHECKPOINT",
    "quota":     "QUOTA CHECKPOINT",
    "manual":    "MANUAL CHECKPOINT",
    "emergency": "EMERGENCY CHECKPOINT",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n) if n else "—"


def _fmt_time(s: int) -> str:
    if not s:
        return "—"
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    h, m = s // 3600, (s % 3600) // 60
    return f"{h}h {m}m" if m else f"{h}h"


def _compact_headroom_pct(context_pct: float, context_window: int) -> int:
    """Return % of context remaining before Claude Code's auto-compact fires.

    Claude Code's auto-compact threshold (the 'auto' default) is ~82% of the
    context window, confirmed by observing ctx:80% alongside '2% until
    auto-compact' in the terminal.  CLAUDE_CODE_AUTO_COMPACT_WINDOW can
    override this; if set to a token count we use that, otherwise fall back to
    the 0.82 constant.
    """
    raw = os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "").strip()
    if raw and raw != "auto":
        try:
            threshold_pct = int(raw) / context_window
        except ValueError:
            threshold_pct = 0.82
    else:
        threshold_pct = 0.82
    headroom = max(0.0, threshold_pct - context_pct)
    return round(headroom / threshold_pct * 100)


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
    autonomous: bool = False,
    project_path: str = "",
) -> Optional[str]:
    """
    Generate a session summary card PNG.
    Returns temp file path on success, None on failure. Caller deletes the file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.gridspec import GridSpec
    except ImportError:
        return None

    goals  = goals_completed or []
    files  = files_changed or []
    has_tl = bool(context_history and len(context_history) >= 4)

    accent = _ACCENT.get(trigger_type, _BLUE)
    title  = _LABEL.get(trigger_type, trigger_type.upper())

    # ── Hero content ─────────────────────────────────────────────────────
    ctx_pct    = round(cost_summary.get("context_pct", 0) * 100)
    in_tok     = cost_summary.get("context_tokens", 0)
    out_tok    = cost_summary.get("output_tokens", 0)
    turns      = cost_summary.get("turns", 0)
    user_turns = cost_summary.get("user_turns", 0)
    project_name = os.path.basename(project_path.rstrip("/")) if project_path else ""

    if trigger_type == "stop" and autonomous:
        hero_val  = "0"
        hero_top  = "developer interruptions"
        hero_sub  = f"Claude ran fully autonomously  ·  {_fmt_time(duration_seconds)}"
        hero_col  = _GREEN
    elif trigger_type == "context":
        hero_val  = f"{ctx_pct}%"
        hero_top  = "context at checkpoint"
        ctx_window = cost_summary.get("context_window", 200_000)
        headroom   = _compact_headroom_pct(cost_summary.get("context_pct", 0), ctx_window)
        hero_sub  = (f"{headroom}% headroom before auto-compact — intercepted cleanly"
                     if headroom > 0 else "auto-compact intercepted — state saved to git")
        hero_col  = accent
    elif trigger_type == "quota":
        hero_val  = "PAUSED"
        hero_top  = "quota limit reached"
        hero_sub  = "state saved to git  ·  auto-resumes at quota reset"
        hero_col  = accent
    else:
        hero_val  = _fmt_time(duration_seconds) if duration_seconds else str(turns)
        hero_top  = "session duration" if duration_seconds else "turns"
        hero_sub  = f"{turns} turns  ·  {_fmt_tokens(in_tok)} input tokens"
        hero_col  = _BLUE

    # ── Figure layout ────────────────────────────────────────────────────
    content_rows = max(len(goals[:4]), len(files[:6]))
    base_h = 8.8 if has_tl else 7.0
    fig_h  = base_h + max(0, content_rows - 3) * 0.22

    fig = plt.figure(figsize=(12, fig_h), facecolor=_BG)

    if has_tl:
        gs  = GridSpec(2, 1, figure=fig,
                       height_ratios=[3.0, 1.2],
                       top=0.97, bottom=0.03, left=0.02, right=0.98,
                       hspace=0.06)
        ax  = fig.add_subplot(gs[0])
        tax = fig.add_subplot(gs[1])
    else:
        gs  = GridSpec(1, 1, figure=fig,
                       top=0.97, bottom=0.03, left=0.02, right=0.98)
        ax  = fig.add_subplot(gs[0])
        tax = None

    # ── Main card ─────────────────────────────────────────────────────────
    ax.set_facecolor(_CARD)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for sp in ax.spines.values():
        sp.set_edgecolor(_BORDER)
        sp.set_linewidth(0.8)
        sp.set_visible(True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Header
    ax.text(0.03, 0.948, "askr", color=accent, fontsize=10,
            fontweight="bold", va="top", transform=ax.transAxes,
            fontfamily="monospace")
    ax.text(0.03, 0.908, title, color=_WHITE, fontsize=18,
            fontweight="bold", va="top", transform=ax.transAxes)
    project_label = f"{project_name}  ·  " if project_name else ""
    ax.text(0.972, 0.948, f"{project_label}{developer}  ·  {ts}",
            color=_MUTED, fontsize=9, va="top", ha="right",
            transform=ax.transAxes)

    # Hero number
    ax.text(0.5, 0.740, hero_val, color=hero_col, fontsize=58,
            fontweight="bold", ha="center", va="center",
            transform=ax.transAxes)
    ax.text(0.5, 0.630, hero_top, color=_MUTED, fontsize=11,
            ha="center", va="center", transform=ax.transAxes,
            fontweight="bold")
    ax.text(0.5, 0.578, hero_sub, color=_DIM, fontsize=9,
            ha="center", va="center", transform=ax.transAxes)

    # Divider
    ax.axhline(y=0.530, color=_BORDER, linewidth=0.8, xmin=0.03, xmax=0.97)

    # Stats row
    turns_label = f"messages ({turns} exchanges)" if user_turns else f"exchanges"
    turns_val   = str(user_turns) if user_turns else str(turns)
    stats = [
        (_fmt_tokens(in_tok),         "input tokens",    _TEXT),
        (_fmt_tokens(out_tok),        "output tokens",   _TEXT),
        (f"{ctx_pct}%",              "ctx window",       _AMBER if ctx_pct >= 60 else _TEXT),
        (turns_val,                   turns_label,        _TEXT),
        (_fmt_time(duration_seconds), "duration",         _BLUE),
    ]
    sw = 1.0 / len(stats)
    for i, (v, lbl, col) in enumerate(stats):
        x = (i + 0.5) * sw
        ax.text(x, 0.465, v, color=col, fontsize=16, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes)
        ax.text(x, 0.403, lbl, color=_MUTED, fontsize=8,
                ha="center", va="center", transform=ax.transAxes)

    # Divider
    ax.axhline(y=0.360, color=_BORDER, linewidth=0.8, xmin=0.03, xmax=0.97)

    # Goals + Files
    L, R, y0 = 0.03, 0.52, 0.315

    if goals:
        ax.text(L, y0, "Goals completed", color=_GREEN, fontsize=8,
                fontweight="bold", va="top", transform=ax.transAxes)
        for i, g in enumerate(goals[:4]):
            ax.text(L, y0 - 0.056 * (i + 1), f"✓  {g[:56]}",
                    color=_GREEN, fontsize=8.5, va="top",
                    transform=ax.transAxes, fontfamily="monospace")

    if files:
        ax.text(R, y0, "Files changed", color=_MUTED, fontsize=8,
                fontweight="bold", va="top", transform=ax.transAxes)
        for i, f in enumerate(files[:6]):
            ax.text(R, y0 - 0.056 * (i + 1), f,
                    color=_MUTED, fontsize=8, va="top",
                    transform=ax.transAxes, fontfamily="monospace")
        if len(files) > 6:
            ax.text(R, y0 - 0.056 * 7, f"+{len(files) - 6} more",
                    color=_DIM, fontsize=8, va="top", transform=ax.transAxes)

    # ── Timeline (context checkpoints only) ───────────────────────────────
    if tax and context_history:
        tax.set_facecolor(_CARD)
        for sp in tax.spines.values():
            sp.set_edgecolor(_BORDER)
            sp.set_linewidth(0.5)

        xs = list(range(len(context_history)))
        ys = [c * 100 for c in context_history]

        tax.fill_between(xs, ys, alpha=0.10, color=accent, zorder=1)
        tax.plot(xs, ys, color=accent, linewidth=2.0, zorder=3)

        # Trigger marker
        tax.axvline(x=xs[-1], color=_AMBER, linewidth=1.2,
                    linestyle="--", alpha=0.8, zorder=4)
        tax.text(max(xs[-1] - 0.4, 0), min(ys[-1] + 3, 97),
                 "checkpoint", color=_AMBER, fontsize=7,
                 ha="right", va="bottom")

        # 65% threshold
        tax.axhline(y=65, color=_RED, linewidth=0.7,
                    linestyle=":", alpha=0.6, zorder=2)
        tax.text(0.5, 66, "65% threshold", color=_RED,
                 fontsize=7, va="bottom")

        tax.set_ylim(0, 105)
        tax.set_ylabel("context %", color=_MUTED, fontsize=8)
        tax.set_xlabel("turn", color=_MUTED, fontsize=8)
        tax.tick_params(colors=_MUTED, labelsize=7)
        tax.yaxis.label.set_color(_MUTED)
        tax.xaxis.label.set_color(_MUTED)

    fd, path = tempfile.mkstemp(suffix=".png", prefix="askr_card_")
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
    total_tokens: int,
    goals_completed: list[str] | None = None,
    goals_open: list[str] | None = None,
) -> Optional[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.gridspec import GridSpec
    except ImportError:
        return None

    goals_completed = goals_completed or []
    goals_open      = goals_open or []

    fig = plt.figure(figsize=(12, 6.5), facecolor=_BG)
    gs  = GridSpec(1, 1, figure=fig,
                   top=0.96, bottom=0.04, left=0.02, right=0.98)
    ax  = fig.add_subplot(gs[0])
    ax.set_facecolor(_CARD)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for sp in ax.spines.values():
        sp.set_edgecolor(_BORDER)
        sp.set_linewidth(0.8)
        sp.set_visible(True)

    ax.text(0.03, 0.948, "askr", color=_BLUE, fontsize=10,
            fontweight="bold", va="top", transform=ax.transAxes,
            fontfamily="monospace")
    ax.text(0.03, 0.908, "MORNING REPORT", color=_WHITE, fontsize=18,
            fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0.972, 0.948, date, color=_MUTED, fontsize=9,
            va="top", ha="right", transform=ax.transAxes)

    # Hero: sessions run autonomous
    ax.text(0.5, 0.740, str(sessions), color=_BLUE, fontsize=58,
            fontweight="bold", ha="center", va="center",
            transform=ax.transAxes)
    ax.text(0.5, 0.630, "autonomous sessions", color=_MUTED, fontsize=11,
            ha="center", va="center", transform=ax.transAxes,
            fontweight="bold")
    ax.text(0.5, 0.578, f"Claude worked unattended for {_fmt_time(total_seconds)}",
            color=_DIM, fontsize=9, ha="center", va="center",
            transform=ax.transAxes)

    ax.axhline(y=0.530, color=_BORDER, linewidth=0.8, xmin=0.03, xmax=0.97)

    stats = [
        (_fmt_time(total_seconds),    "total active",   _BLUE),
        (_fmt_tokens(total_tokens),   "tokens used",    _TEXT),
        (str(len(goals_completed)),   "goals shipped",  _GREEN),
        (str(len(goals_open)),        "goals open",     _AMBER if goals_open else _TEXT),
    ]
    sw = 1.0 / len(stats)
    for i, (v, lbl, col) in enumerate(stats):
        x = (i + 0.5) * sw
        ax.text(x, 0.465, v, color=col, fontsize=18, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes)
        ax.text(x, 0.403, lbl, color=_MUTED, fontsize=8,
                ha="center", va="center", transform=ax.transAxes)

    ax.axhline(y=0.360, color=_BORDER, linewidth=0.8, xmin=0.03, xmax=0.97)

    L, R, y0 = 0.03, 0.52, 0.315

    if goals_completed:
        ax.text(L, y0, "Shipped", color=_GREEN, fontsize=8,
                fontweight="bold", va="top", transform=ax.transAxes)
        for i, g in enumerate(goals_completed[:4]):
            ax.text(L, y0 - 0.056 * (i + 1), f"✓  {g[:56]}",
                    color=_GREEN, fontsize=8.5, va="top",
                    transform=ax.transAxes, fontfamily="monospace")

    if goals_open:
        ax.text(R, y0, "In progress", color=_AMBER, fontsize=8,
                fontweight="bold", va="top", transform=ax.transAxes)
        for i, g in enumerate(goals_open[:4]):
            ax.text(R, y0 - 0.056 * (i + 1), f"→  {g[:56]}",
                    color=_MUTED, fontsize=8.5, va="top",
                    transform=ax.transAxes, fontfamily="monospace")

    fd, path = tempfile.mkstemp(suffix=".png", prefix="askr_report_")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    return path
