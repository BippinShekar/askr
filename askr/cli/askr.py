#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.utils.display import console
from askr.state.config import (
    get_state_dir, load_developer, save_developer,
    ensure_state_dir, state_path, save_project_path, load_project_path
)

ASKR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOKS_DIR = os.path.join(ASKR_DIR, "askr", "hooks")
CLAUDE_SETTINGS = os.path.join(".claude", "settings.json")
SNAPSHOT_PATH = os.path.join(".llm_snapshot", "summary.json")

HOOK_MAP = {
    "SessionStart":       "session_start.py",
    "UserPromptSubmit":   "user_prompt_submit.py",
    "PostToolUse":        "post_tool_use.py",
    "Stop":               "stop.py",
    "PreCompact":         "pre_compact.py",
    "Notification":       "notification.py",
}

_STATS_PATH = os.path.expanduser("~/.config/askr/session_stats.json")


def _python_cmd() -> str:
    venv_python = os.path.join(ASKR_DIR, "venv", "bin", "python")
    return venv_python if os.path.exists(venv_python) else sys.executable


def _hook_command(hook_file: str) -> str:
    return f"{_python_cmd()} {os.path.join(HOOKS_DIR, hook_file)}"


def _load_claude_settings() -> dict:
    if os.path.exists(CLAUDE_SETTINGS):
        with open(CLAUDE_SETTINGS) as f:
            return json.load(f)
    return {}


def _save_claude_settings(data: dict):
    os.makedirs(".claude", exist_ok=True)
    with open(CLAUDE_SETTINGS, "w") as f:
        json.dump(data, f, indent=2)


def _install_hooks():
    settings = _load_claude_settings()
    hooks = settings.setdefault("hooks", {})

    for event, hook_file in HOOK_MAP.items():
        cmd = _hook_command(hook_file)
        entry = {"type": "command", "command": cmd, "timeout": 15}

        existing = hooks.get(event, [])
        already_installed = any(
            h.get("command", "") == cmd
            for group in existing
            for h in group.get("hooks", [])
        )

        if not already_installed:
            hooks[event] = existing + [{"hooks": [entry]}]

    _save_claude_settings(settings)


def _install_statusline():
    settings = _load_claude_settings()
    cmd = f"{_python_cmd()} {os.path.join(ASKR_DIR, 'askr', 'cli', 'askr.py')} status --line"
    existing = settings.get("statusLine", {})
    if existing.get("command") != cmd or existing.get("type") != "command":
        settings["statusLine"] = {"type": "command", "command": cmd}
        _save_claude_settings(settings)


def _install_ide_extension():
    """Install the status bar extension into VS Code and Cursor extension directories."""
    import shutil

    src = os.path.join(ASKR_DIR, "askr", "ide", "vscode-extension")
    ext_name = "askr.askr-status-1.0.0"
    installed = []

    candidates = [
        os.path.expanduser("~/.cursor/extensions"),
        os.path.expanduser("~/.vscode/extensions"),
    ]

    for ext_dir in candidates:
        if not os.path.isdir(ext_dir):
            continue
        dest = os.path.join(ext_dir, ext_name)
        shutil.copytree(src, dest, dirs_exist_ok=True)
        installed.append(ext_dir)

    return installed


def _install_launchd() -> tuple[bool, str]:
    """
    Install and load a launchd agent so the lifecycle daemon starts at login.
    Returns (success, plist_path).
    """
    plist_label = "com.askr.daemon"
    plist_path  = os.path.expanduser(f"~/Library/LaunchAgents/{plist_label}.plist")
    log_path    = os.path.expanduser("~/.config/askr/daemon.log")
    lifecycle   = os.path.join(ASKR_DIR, "askr", "session", "lifecycle.py")

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{_python_cmd()}</string>
        <string>{lifecycle}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{log_path}</string>
</dict>
</plist>"""

    try:
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, "w") as f:
            f.write(plist)

        import subprocess as _sp
        _sp.run(["launchctl", "unload", plist_path], capture_output=True)
        result = _sp.run(["launchctl", "load", plist_path], capture_output=True, text=True)
        return result.returncode == 0, plist_path
    except Exception as e:
        return False, str(e)


def _power_source() -> str:
    try:
        import subprocess as _sp
        r = _sp.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        return "ac" if "AC Power" in r.stdout else "battery"
    except Exception:
        return "unknown"


def _create_skeleton_files(developer: str) -> tuple[list, list]:
    templates_dir = os.path.join(ASKR_DIR, "askr", "state", "templates")
    ensure_state_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # architecture.md and implementation_state.md get generated from the codebase
    # only fall back to template if generation fails
    template_only_files = {
        f"handover_{developer}.md":     "handover_template.md",
        f"current_task_{developer}.md": "current_task_template.md",
        "decisions.md":                 "decisions_template.md",
        "blockers.md":                  "blockers_template.md",
        "goals.md":                     "goals_template.md",
    }

    created = []
    skipped = []

    for target, template in template_only_files.items():
        target_path = state_path(target)
        if os.path.exists(target_path):
            skipped.append(target)
            continue
        template_path = os.path.join(templates_dir, template)
        if os.path.exists(template_path):
            with open(template_path) as f:
                content = f.read()
            from datetime import date as _date
            content = (content
                .replace("{developer}", developer)
                .replace("{timestamp}", timestamp)
                .replace("{date}", _date.today().strftime("%Y-%m-%d")))
            with open(target_path, "w") as f:
                f.write(content)
            created.append(target)

    return created, skipped


def _generate_architecture_from_snapshot(developer: str):
    if not os.path.exists(SNAPSHOT_PATH):
        return False

    try:
        import json as _json
        with open(SNAPSHOT_PATH) as f:
            snapshot = _json.load(f)

        if not snapshot:
            return False

        from askr.qa.context_loader import load_fast_context
        from askr.clients.claude import call_claude
        from askr.state.writer import update_architecture, update_implementation_section

        fast_ctx = load_fast_context()

        inventory_lines = [
            f"{e.get('file')} - {e.get('purpose', '')}"
            for e in snapshot
            if e.get("file") and e.get("purpose")
        ]
        inventory = "\n".join(inventory_lines)

        # Generate architecture.md
        arch_path = state_path("architecture.md")
        if not os.path.exists(arch_path):
            console.print("  [dim]generating architecture.md from codebase...[/dim]")

            prompt = f"""Write architecture.md for this codebase. Be factual and brief. Only describe what is actually in the code.

CONTEXT:
{fast_ctx}

ALL FILES:
{inventory}

Format exactly as:
## System Overview
[what this system does - 2 sentences max]

## Modules
[each module/package and what it owns - bullet list]

## Key Patterns
[auth, API style, data layer - only what is clearly visible]

## External Dependencies
[external services and libraries that matter architecturally]

No placeholders. No speculation. Only what is in the code."""

            arch_content = call_claude(
                "You write concise, factual technical documentation.",
                prompt,
                mode="default",
                query_preview="architecture.md generation"
            )
            # strip leading # Architecture header if LLM added one - writer adds its own
            lines = arch_content.strip().splitlines()
            if lines and lines[0].strip().lower().startswith("# architecture"):
                arch_content = "\n".join(lines[1:]).lstrip()
            update_architecture(arch_content)
            console.print("  [green]✓[/green] [dim]architecture.md - generated from codebase[/dim]")
        else:
            console.print("  [dim]- skipped architecture.md (already exists)[/dim]")

        # Populate implementation_state.md with what is already built
        impl_path = state_path("implementation_state.md")
        if not os.path.exists(impl_path):
            top_files = sorted(snapshot, key=lambda x: x.get("_score", 0), reverse=True)[:25]
            completed_lines = [
                f"- {e.get('file')} - {e.get('purpose', '')}"
                for e in top_files
                if e.get("file") and e.get("purpose")
            ]
            completed = "\n".join(completed_lines) if completed_lines else "[nothing yet]"

            update_implementation_section(
                f"### In Progress\n\n[nothing - session not started]\n\n"
                f"### Completed\n\n{completed}\n\n"
                f"### Files Owned\n\n[not assigned yet]",
                developer
            )
            console.print("  [green]✓[/green] [dim]implementation_state.md - populated from snapshot[/dim]")
        else:
            console.print("  [dim]- skipped implementation_state.md (already exists)[/dim]")

        return True

    except Exception as e:
        console.print(f"  [yellow]⚠ snapshot generation failed: {e}[/yellow]")
        return False


def _create_fallback_generated_files(developer: str):
    templates_dir = os.path.join(ASKR_DIR, "askr", "state", "templates")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for target, template in [
        ("architecture.md", "architecture_template.md"),
        ("implementation_state.md", "implementation_state_template.md"),
    ]:
        target_path = state_path(target)
        if not os.path.exists(target_path):
            template_path = os.path.join(templates_dir, template)
            if os.path.exists(template_path):
                with open(template_path) as f:
                    content = f.read()
                content = content.replace("{developer}", developer).replace("{timestamp}", timestamp)
                with open(target_path, "w") as f:
                    f.write(content)


def _update_gitignore():
    gitignore = ".gitignore"
    entries = [".llm_snapshot/", ".askr_log"]
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            existing = f.read()
        additions = [e for e in entries if e not in existing]
        if additions:
            with open(gitignore, "a") as f:
                f.write("\n# askr\n" + "\n".join(additions) + "\n")


def cmd_init():
    console.print()
    console.rule("[bold]askr init[/]", style="dim")
    console.print()

    existing_dev = load_developer()
    console.print(f"  [dim]developer name (current: {existing_dev})[/dim]")
    try:
        raw = input("  enter name (or press enter to keep): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n  [dim]cancelled[/dim]\n")
        return

    developer = raw if raw else existing_dev
    save_developer(developer)
    save_project_path(os.getcwd())
    console.print(f"  [green]✓[/green] [dim]developer:[/dim] [bold]{developer}[/bold]")
    console.print(f"  [green]✓[/green] [dim]project:[/dim] [bold]{os.getcwd()}[/bold]")
    console.print()

    # Create session-specific files from templates
    created, skipped = _create_skeleton_files(developer)
    for f in created:
        console.print(f"  [green]✓[/green] created  [dim]{f}[/dim]")
    for f in skipped:
        console.print(f"  [dim]- skipped {f} (already exists)[/dim]")

    # Generate architecture.md and implementation_state.md from codebase snapshot
    has_snapshot = os.path.exists(SNAPSHOT_PATH)
    if has_snapshot:
        generated = _generate_architecture_from_snapshot(developer)
        if not generated:
            _create_fallback_generated_files(developer)
    else:
        console.print()
        console.print("  [yellow]no codebase snapshot found[/yellow]")
        console.print("  [dim]run[/dim] [bold]ask init[/bold] [dim]first to index your codebase,[/dim]")
        console.print("  [dim]then re-run[/dim] [bold]askr init[/bold] [dim]to generate a real architecture.md[/dim]")
        _create_fallback_generated_files(developer)

    console.print()

    _install_hooks()
    for event in HOOK_MAP:
        console.print(f"  [green]✓[/green] hook  [dim]{event}[/dim]")

    _install_statusline()
    console.print("  [green]✓[/green] statusLine [dim](Claude Code terminal pane)[/dim]")

    installed_dirs = _install_ide_extension()
    if installed_dirs:
        for d in installed_dirs:
            ide = "Cursor" if "cursor" in d.lower() else "VS Code"
            console.print(f"  [green]✓[/green] status bar extension → [dim]{ide}[/dim]  [yellow](reload window to activate)[/yellow]")
    else:
        console.print("  [dim]- IDE extension: no ~/.cursor/extensions or ~/.vscode/extensions found[/dim]")

    ok, plist_path = _install_launchd()
    if ok:
        console.print("  [green]✓[/green] daemon → [dim]launchd (starts at login, always-on)[/dim]")
    else:
        console.print(f"  [yellow]⚠ launchd install failed:[/yellow] [dim]{plist_path}[/dim]")

    power = _power_source()
    if power == "battery":
        console.print()
        console.print("  [yellow]⚠ on battery[/yellow]  [dim]— caffeinate cannot prevent sleep if lid is closed.")
        console.print("  [dim]  Plug in for reliable overnight runs.[/dim]")

    console.print()
    _update_gitignore()

    console.print("  [dim]state files:[/dim] [bold]askr_state/[/bold]")
    console.print("  [dim]commit askr_state/ to git so your team shares the same ground truth[/dim]")
    console.print()
    console.print("  [green]done[/green]  - open Claude Code and Askr will track from here\n")


def _reset_countdown(reset_at_iso: str) -> str:
    """Format time remaining until quota reset as '↺2h34m' or '↺42m'."""
    try:
        from datetime import datetime, timezone
        reset = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
        remaining = (reset - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            return "↺now"
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        return f"↺{h}h{m:02d}m" if h > 0 else f"↺{m}m"
    except Exception:
        return ""


def _statusline_text() -> str:
    """Compact one-line output for 'askr status --line'."""
    try:
        if not os.path.exists(_STATS_PATH):
            return "askr ·"
        with open(_STATS_PATH) as f:
            s = json.load(f)

        ctx_pct    = int(round(s.get("context_pct", 0) * 100))
        ctx_label  = s.get("context_label", "ok")
        reset_at   = s.get("reset_at", "")

        ctx_part   = f"ctx:{ctx_pct}%"
        reset_part = _reset_countdown(reset_at) if reset_at else ""

        label_suffix = {"checkpoint": " ⚠", "near limit": " !", "high": ""}
        suffix = label_suffix.get(ctx_label, "")

        parts = ["askr", ctx_part]
        if reset_part:
            parts.append(reset_part)
        return " ".join(parts) + suffix
    except Exception:
        return "askr ·"


def cmd_status(args: list = None):
    args = args or []

    if "--line" in args:
        print(_statusline_text())
        return

    developer = load_developer()
    console.print()
    console.rule("[bold]askr status[/]", style="dim")
    console.print()
    console.print(f"  [dim]developer[/dim]   [bold]{developer}[/bold]")
    console.print(f"  [dim]state dir[/dim]   {'[green]found[/green]' if os.path.isdir(get_state_dir()) else '[red]missing - run askr init[/red]'}")
    console.print(f"  [dim]snapshot[/dim]    {'[green]found[/green]' if os.path.exists(SNAPSHOT_PATH) else '[yellow]missing - run ask init[/yellow]'}")

    if os.path.isdir(get_state_dir()):
        handover = state_path(f"handover_{developer}.md")
        arch = state_path("architecture.md")
        console.print(f"  [dim]handover[/dim]    {'[green]present[/green]' if os.path.exists(handover) else '[yellow]missing[/yellow]'}")
        console.print(f"  [dim]architecture[/dim] {'[green]present[/green]' if os.path.exists(arch) else '[yellow]missing[/yellow]'}")
        console.print(f"  [dim]hooks[/dim]       {'[green]configured[/green]' if os.path.exists(CLAUDE_SETTINGS) else '[yellow]not configured - run askr init[/yellow]'}")

    if os.path.exists(_STATS_PATH):
        try:
            import time as _time
            stats_age = _time.time() - os.path.getmtime(_STATS_PATH)
            with open(_STATS_PATH) as f:
                s = json.load(f)
            reset_at = s.get("reset_at", "")
            console.print()
            if stats_age > 600:
                console.print(f"  [dim]context[/dim]     [dim]no active session[/dim]")
            else:
                ctx_pct    = int(round(s.get("context_pct", 0) * 100))
                ctx_tokens = s.get("context_tokens", 0)
                ctx_window = s.get("context_window", 200000)
                ctx_label  = s.get("context_label", "ok")
                label_map = {"high": "[yellow]high[/yellow]", "near limit": "[red]near limit[/red]", "checkpoint": "[bold red]checkpoint[/bold red]"}
                label_str = f"  {label_map[ctx_label]}" if ctx_label in label_map else ""
                console.print(f"  [dim]context[/dim]     [bold]{ctx_pct}%[/bold] ({ctx_tokens:,} / {ctx_window:,} — this chat only){label_str}")
            if reset_at:
                countdown = _reset_countdown(reset_at)
                console.print(f"  [dim]quota reset[/dim]  {countdown}  [dim](check claude.ai/settings for actual %)[/dim]")
        except Exception:
            console.print()
            console.print(f"  [dim]session[/dim]     {_statusline_text()}")

    console.print()


def cmd_goals():
    from askr.state.goals import load_today_goals, load_open_goals, load_done_today
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")

    console.print()
    console.rule(f"[bold]goals - {today}[/]", style="dim")
    console.print()

    today_goals = load_today_goals()
    if today_goals:
        console.print("  [bold]today[/bold]")
        for g in today_goals:
            console.print(f"  [dim]- [ ][/dim] {g}")
    else:
        console.print("  [dim]no goals set for today[/dim]")
        console.print("  [dim]add one:[/dim] [bold]askr goal add \"...\"[/bold]")

    open_goals = load_open_goals()
    backlog = [g for g in open_goals if g not in today_goals]
    if backlog:
        console.print()
        console.print("  [bold]backlog[/bold]")
        for g in backlog:
            console.print(f"  [dim]- [ ][/dim] {g}")

    done = load_done_today()
    if done:
        console.print()
        console.print("  [bold]done today[/bold]")
        for g in done:
            console.print(f"  [green]- [x][/green] {g}")

    console.print()


def cmd_goal(args: list[str]):
    from askr.state.goals import add_goal, complete_goal

    if not args:
        console.print("\n  [bold]askr goal[/bold]")
        console.print("  [dim]askr goal add \"finish the auth layer\"[/dim]")
        console.print("  [dim]askr goal add \"ship phase 2\" --backlog[/dim]")
        console.print("  [dim]askr goal done \"finish the auth layer\"[/dim]\n")
        return

    sub = args[0]

    if sub == "add":
        if len(args) < 2:
            console.print("\n  [red]usage: askr goal add \"goal text\"[/red]\n")
            return
        text = args[1]
        section = "backlog" if "--backlog" in args else "today"
        add_goal(text, section)
        label = "backlog" if section == "backlog" else "today"
        console.print(f"\n  [green]✓[/green] added to {label}: [bold]{text}[/bold]\n")

    elif sub == "done":
        if len(args) < 2:
            console.print("\n  [red]usage: askr goal done \"goal text\"[/red]\n")
            return
        text = args[1]
        if complete_goal(text):
            console.print(f"\n  [green]✓[/green] marked done: [bold]{text}[/bold]\n")
        else:
            console.print(f"\n  [yellow]not found:[/yellow] {text}\n")
            console.print("  [dim]run[/dim] [bold]askr goals[/bold] [dim]to see open goals[/dim]\n")

    else:
        console.print(f"\n  [yellow]unknown: askr goal {sub}[/yellow]")
        console.print("  [dim]use: add / done[/dim]\n")


def cmd_launch(args: list):
    """
    askr launch — show daemon status and session info.
    The daemon runs automatically via launchd (installed by askr init).
    Use --stop to manually kill it; it will restart at next login.
    Use --restart to force an immediate restart.
    """
    from askr.session.lifecycle import daemon_is_running, stop_daemon
    import subprocess as _subprocess

    log_path = os.path.expanduser("~/.config/askr/daemon.log")

    if "--stop" in args:
        if stop_daemon():
            console.print("\n  [green]✓[/green] daemon stopped")
            console.print("  [dim]it will restart at next login (launchd managed)[/dim]")
            console.print(f"  [dim]to disable permanently: launchctl unload ~/Library/LaunchAgents/com.askr.daemon.plist[/dim]\n")
        else:
            console.print("\n  [dim]no daemon running[/dim]\n")
        return

    if "--restart" in args:
        stop_daemon()
        import time as _time
        _time.sleep(0.5)
        lifecycle_script = os.path.join(ASKR_DIR, "askr", "session", "lifecycle.py")
        _subprocess.Popen(
            [_python_cmd(), lifecycle_script],
            stdout=open(log_path, "a"),
            stderr=open(log_path, "a"),
            start_new_session=True,
        )
        _time.sleep(0.5)

    console.print()
    console.rule("[bold]askr launch[/]", style="dim")
    console.print()

    running = daemon_is_running()
    if running:
        console.print("  [green]●[/green] daemon running  [dim](always-on via launchd)[/dim]")
    else:
        console.print("  [red]○[/red] daemon not running")
        console.print("  [dim]reinstall:[/dim] [bold]askr init[/bold]  [dim]or restart:[/dim] [bold]askr launch --restart[/bold]")

    power = _power_source()
    if power == "battery":
        console.print("  [yellow]⚠ on battery[/yellow]  [dim]— plug in for overnight runs[/dim]")

    try:
        from askr.state.goals import load_today_goals, load_open_goals
        today = load_today_goals()
        goals = today or load_open_goals()
        if goals:
            console.print(f"  [dim]next goal:[/dim] {goals[0]}")
        else:
            console.print("  [dim]no goals — add one:[/dim] [bold]askr goal add \"...\"[/bold]")
    except Exception:
        pass

    if os.path.exists(_STATS_PATH):
        console.print(f"  [dim]session:[/dim] {_statusline_text()}")

    console.print()
    console.print(f"  [dim]log:[/dim] {log_path}")
    console.print(f"  [dim]stop:[/dim] [bold]askr launch --stop[/bold]")
    console.print()


def main():
    if len(sys.argv) < 2:
        console.print("\n  [bold]askr[/bold]  [dim]session orchestration for Claude Code[/dim]")
        console.print()
        console.print("  [dim]askr init                - set up in this project[/dim]")
        console.print("  [dim]askr status              - show current state[/dim]")
        console.print("  [dim]askr goals               - show today's goals[/dim]")
        console.print("  [dim]askr goal add \"...\"      - add a goal for today[/dim]")
        console.print("  [dim]askr goal done \"...\"     - mark a goal complete[/dim]")
        console.print("  [dim]askr launch              - show daemon status (always-on via launchd)[/dim]")
        console.print("  [dim]askr launch --stop       - stop daemon manually[/dim]")
        console.print("  [dim]askr launch --restart    - restart daemon now[/dim]")
        console.print("  [dim]askr log                 - session history (Phase 3)[/dim]")
        console.print()
        sys.exit(0)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "init":
        cmd_init()
    elif cmd == "status":
        cmd_status(rest)
    elif cmd == "goals":
        cmd_goals()
    elif cmd == "goal":
        cmd_goal(rest)
    elif cmd == "launch":
        cmd_launch(rest)
    else:
        console.print(f"\n  [yellow]askr {cmd}[/yellow] [dim]- not yet implemented, see roadmap.md[/dim]\n")


if __name__ == "__main__":
    main()
