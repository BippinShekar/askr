#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.utils.display import console
from askr.state.config import (
    get_state_dir, load_developer, save_developer,
    ensure_state_dir, state_path, save_project_path
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
}


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
            content = content.replace("{developer}", developer).replace("{timestamp}", timestamp)
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

    console.print()
    _update_gitignore()

    console.print("  [dim]state files:[/dim] [bold]askr_state/[/bold]")
    console.print("  [dim]commit askr_state/ to git so your team shares the same ground truth[/dim]")
    console.print()
    console.print("  [green]done[/green]  - open Claude Code and Askr will track from here\n")


def cmd_status():
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
