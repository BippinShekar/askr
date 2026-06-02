#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.utils.display import console
from askr.state.config import STATE_DIR, load_developer, save_developer, ensure_state_dir, state_path

ASKR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOKS_DIR = os.path.join(ASKR_DIR, "askr", "hooks")
CLAUDE_SETTINGS = os.path.join(".claude", "settings.json")

HOOK_MAP = {
    "SessionStart":       "session_start.py",
    "UserPromptSubmit":   "user_prompt_submit.py",
    "PostToolUse":        "post_tool_use.py",
    "Stop":               "stop.py",
    "PreCompact":         "pre_compact.py",
}


def _python_cmd() -> str:
    venv_python = os.path.join(ASKR_DIR, "venv", "bin", "python")
    return venv_python if os.path.exists(venv_python) else sys.executable


def _hook_command(hook_file: str) -> str:
    python = _python_cmd()
    script = os.path.join(HOOKS_DIR, hook_file)
    return f"{python} {script}"


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


def _create_state_files(developer: str):
    templates_dir = os.path.join(ASKR_DIR, "askr", "state", "templates")
    ensure_state_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    file_map = {
        f"handover_{developer}.md":       "handover_template.md",
        f"current_task_{developer}.md":   "current_task_template.md",
        "decisions.md":                   "decisions_template.md",
        "implementation_state.md":        "implementation_state_template.md",
        "architecture.md":                "architecture_template.md",
        "blockers.md":                    "blockers_template.md",
    }

    created = []
    skipped = []

    for target, template in file_map.items():
        target_path = state_path(target)
        template_path = os.path.join(templates_dir, template)

        if os.path.exists(target_path):
            skipped.append(target)
            continue

        if os.path.exists(template_path):
            with open(template_path) as f:
                content = f.read()
            content = content.replace("{developer}", developer)
            content = content.replace("{timestamp}", timestamp)
            with open(target_path, "w") as f:
                f.write(content)
            created.append(target)

    return created, skipped


def _update_gitignore():
    gitignore = ".gitignore"
    entries = [".llm_snapshot/", ".askr_history", ".askr_log"]

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
    console.print(f"  [dim]developer name[/dim] [dim](current: {existing_dev})[/dim]")
    try:
        raw = input("  enter name (or press enter to keep): ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("\n  [dim]cancelled[/dim]\n")
        return

    developer = raw if raw else existing_dev
    save_developer(developer)
    console.print(f"  [green]✓[/green] [dim]developer set to[/dim] [bold]{developer}[/bold]")
    console.print()

    created, skipped = _create_state_files(developer)

    for f in created:
        console.print(f"  [green]✓[/green] created  [dim]askr/state/{f}[/dim]")
    for f in skipped:
        console.print(f"  [dim]- skipped askr/state/{f} (already exists)[/dim]")

    console.print()

    _install_hooks()
    for event in HOOK_MAP:
        console.print(f"  [green]✓[/green] hook registered  [dim]{event}[/dim]")

    console.print()

    _update_gitignore()

    console.print("  [dim]state files are in[/dim] [bold]askr/state/[/bold]")
    console.print("  [dim]commit them to git so your team shares the same ground truth[/dim]")
    console.print()
    console.print("  [green]done[/green]  - start Claude Code and Askr will track the session\n")


def cmd_status():
    developer = load_developer()
    console.print()
    console.rule("[bold]askr status[/]", style="dim")
    console.print()
    console.print(f"  [dim]developer[/dim]  [bold]{developer}[/bold]")
    console.print(f"  [dim]state dir[/dim]  {'[green]found[/green]' if os.path.isdir(STATE_DIR) else '[red]not found - run askr init[/red]'}")

    if os.path.isdir(STATE_DIR):
        handover = state_path(f"handover_{developer}.md")
        console.print(f"  [dim]handover[/dim]   {'[green]present[/green]' if os.path.exists(handover) else '[yellow]missing[/yellow]'}")

        settings_ok = os.path.exists(CLAUDE_SETTINGS)
        console.print(f"  [dim]hooks[/dim]      {'[green]configured[/green]' if settings_ok else '[yellow]not configured - run askr init[/yellow]'}")

    console.print()


def main():
    if len(sys.argv) < 2:
        console.print("\n  [bold]askr[/bold]  [dim]session orchestration for Claude Code[/dim]")
        console.print()
        console.print("  [dim]askr init      - set up session orchestration in this project[/dim]")
        console.print("  [dim]askr status    - show current session state[/dim]")
        console.print("  [dim]askr launch    - start Claude Code under Askr management (Phase 2)[/dim]")
        console.print("  [dim]askr log       - show session history (Phase 3)[/dim]")
        console.print()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()
    elif cmd == "status":
        cmd_status()
    else:
        console.print(f"\n  [yellow]askr {cmd}[/yellow] [dim]- not yet implemented, see roadmap.md[/dim]\n")


if __name__ == "__main__":
    main()
