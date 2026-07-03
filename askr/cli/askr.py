#!/usr/bin/env python3

import sys
import os
import json
import platform
from datetime import datetime

# Force UTF-8 stdout so Unicode characters render correctly in all terminal
# environments (shell prompt, launchd, etc.) regardless of LANG/LC_ALL.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    "PreToolUse":         "pre_tool_use.py",
    "PostToolUse":        "post_tool_use.py",
    "Stop":               "stop.py",
    "PreCompact":         "pre_compact.py",
    "Notification":       "notification.py",
}

# Minimum tool set for autonomous operation — stop hook expands this over time from JSONL
BASELINE_ALLOWED_TOOLS = ["Bash", "Edit", "Read", "TodoWrite", "WebSearch", "Write"]

# Stop and PreCompact make a Haiku API call for handover generation — need more headroom
# PreToolUse must be fast — it blocks Claude's tool execution until it exits
HOOK_TIMEOUTS = {
    "Stop":        60,
    "PreCompact":  60,
    "PreToolUse":  10,
}

_STATUSLINE_SESSION_ID_CACHE = None


def _statusline_session_id() -> str:
    """
    Claude Code invokes the statusLine command with a JSON payload on stdin
    containing this session's own session_id. Read it so each session shows
    ITS OWN stats — without this, _stats_path's mtime-heuristic fallback picks
    whichever sibling session in the same project happened to fire PostToolUse
    most recently, so the statusline shows another session's numbers instead
    of this one's (looks like the line randomly resets/"collapses").

    Memoized: stdin can only be drained once per process, and _stats_path()
    is called more than once per invocation.
    """
    global _STATUSLINE_SESSION_ID_CACHE
    if _STATUSLINE_SESSION_ID_CACHE is not None:
        return _STATUSLINE_SESSION_ID_CACHE
    session_id = ""
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            if raw:
                session_id = json.loads(raw).get("session_id", "") or ""
        except Exception:
            session_id = ""
    _STATUSLINE_SESSION_ID_CACHE = session_id
    return session_id


def _stats_path() -> str:
    """
    Return this session's own stats file when Claude Code told us the
    session_id via stdin. Falls back to "most-recently-modified stats file
    for the project" only when that's unavailable (e.g. run manually from a
    shell) — that heuristic is wrong whenever 2+ sessions share a project.
    """
    from askr.session.monitor import (
        find_project_root, find_project_stats_files,
        stats_path_for_project, stats_path_for_session,
    )
    project_path = find_project_root()

    session_id = _statusline_session_id()
    if session_id:
        own_path = stats_path_for_session(project_path, session_id)
        if os.path.exists(own_path):
            return own_path

    candidates = find_project_stats_files(project_path)
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return stats_path_for_project(project_path)  # fallback if nothing exists yet


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
        entry = {"type": "command", "command": cmd, "timeout": HOOK_TIMEOUTS.get(event, 15)}

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


def _install_allowed_tools() -> tuple[list, list]:
    """Merge baseline tools into allowedTools (settings.json) and permissions.allow (settings.local.json).
    Returns (new_tools_added, already_present)."""
    settings = _load_claude_settings()
    existing = set(settings.get("allowedTools", []))
    new_tools = [t for t in BASELINE_ALLOWED_TOOLS if t not in existing]
    if new_tools:
        settings["allowedTools"] = sorted(existing | set(BASELINE_ALLOWED_TOOLS))
        _save_claude_settings(settings)

    # permissions.allow is what actually silences tool prompts — seed it at init
    local_path = os.path.join(".claude", "settings.local.json")
    try:
        if os.path.exists(local_path):
            with open(local_path) as f:
                local = json.load(f)
        else:
            local = {}
        perms = local.setdefault("permissions", {})
        existing_allow = set(perms.get("allow", []))
        baseline_set = set(BASELINE_ALLOWED_TOOLS)
        if baseline_set - existing_allow:
            perms["allow"] = sorted(existing_allow | baseline_set)
            os.makedirs(".claude", exist_ok=True)
            with open(local_path, "w") as f:
                json.dump(local, f, indent=2)
    except Exception:
        pass

    return new_tools, [t for t in BASELINE_ALLOWED_TOOLS if t in existing]


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


_CLAUDE_MD_MARKER_START = "<!-- askr:behavioral-start -->"
_CLAUDE_MD_MARKER_END   = "<!-- askr:behavioral-end -->"
_CLAUDE_MD_GUARD_START  = "<!-- askr:guard-start -->"
_CLAUDE_MD_GUARD_END    = "<!-- askr:guard-end -->"

_CLAUDE_MD_SECTION = """\
<!-- askr:behavioral-start -->
## Askr — Behavioral Instructions

These instructions are written by `askr init`. Edit freely — askr will never
overwrite content outside the fenced markers.

- **Be direct.** No preamble, no "Great question!", no "Certainly!". Lead with
  the answer or the action.
- **Flag problems first.** If an approach has a flaw, a missing dependency, or
  conflicts with the existing architecture — say so explicitly *before*
  implementing anything. Do not bury it after paragraphs of praise.
- **No sycophancy.** Do not validate an idea just because the user suggested it.
  If it is wrong or suboptimal, say so plainly and explain why.
- **Concise by default.** One clear sentence beats a paragraph. Use bullet
  points for lists of things. Never pad to appear thorough.
- **Honest uncertainty.** If you do not know, say so. Do not fabricate
  confidence.
<!-- askr:behavioral-end -->"""

_CLAUDE_MD_GUARD_SECTION = """\
<!-- askr:guard-start -->
## Implementation Guard

Before editing any file:
1. Check `askr_state/decisions.jsonl` for settled decisions that affect that file's domain.
2. Check `askr_state/failed_approaches.md` for approaches already tried and rejected.
3. If your planned change contradicts a settled decision or repeats a rejected approach, say so explicitly before implementing — do not proceed silently.
<!-- askr:guard-end -->"""


def _install_claude_md() -> str:
    """
    Write (or update) the askr behavioral + guard sections in CLAUDE.md.
    Preserves all user-written content outside the askr markers.
    Returns 'created', 'updated', or 'unchanged'.
    """
    import re as _re
    claude_md_path = "CLAUDE.md"
    changed = False

    if os.path.exists(claude_md_path):
        with open(claude_md_path) as f:
            content = f.read()
    else:
        content = ""

    # Behavioral section
    if _CLAUDE_MD_MARKER_START in content:
        updated = _re.sub(
            rf"{_re.escape(_CLAUDE_MD_MARKER_START)}.*?{_re.escape(_CLAUDE_MD_MARKER_END)}",
            _CLAUDE_MD_SECTION, content, flags=_re.DOTALL,
        )
        if updated != content:
            content = updated
            changed = True
    else:
        content = content + (f"\n\n{_CLAUDE_MD_SECTION}\n" if content else f"{_CLAUDE_MD_SECTION}\n")
        changed = True

    # Guard section
    if _CLAUDE_MD_GUARD_START in content:
        updated = _re.sub(
            rf"{_re.escape(_CLAUDE_MD_GUARD_START)}.*?{_re.escape(_CLAUDE_MD_GUARD_END)}",
            _CLAUDE_MD_GUARD_SECTION, content, flags=_re.DOTALL,
        )
        if updated != content:
            content = updated
            changed = True
    else:
        content = content + f"\n\n{_CLAUDE_MD_GUARD_SECTION}\n"
        changed = True

    if not changed:
        return "unchanged"

    existed = os.path.exists(claude_md_path)
    with open(claude_md_path, "w") as f:
        f.write(content)
    return "created" if not existed else "updated"


def _install_launchd() -> tuple[bool, str]:
    """
    Install and load a launchd agent so the lifecycle daemon starts at login.
    Returns (success, plist_path).
    """
    plist_label = "com.askr.daemon"
    plist_path  = os.path.expanduser(f"~/Library/LaunchAgents/{plist_label}.plist")
    log_path    = os.path.expanduser("~/.config/askr/daemon.log")
    lifecycle   = os.path.join(ASKR_DIR, "askr", "session", "lifecycle.py")

    # Capture the user's full shell PATH so launchd (which starts with minimal PATH)
    # can find user-installed CLIs like claude.
    try:
        import subprocess as _sp2
        _shell_path = _sp2.run(
            ["zsh", "-l", "-c", "echo $PATH"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or os.environ.get("PATH", "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin")
    except Exception:
        _shell_path = os.environ.get("PATH", "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin")

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
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{_shell_path}</string>
    </dict>
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
        # Idempotent: skip the unload/load cycle entirely when nothing changed
        # and the daemon is already running. Every `askr init` run used to
        # reload unconditionally — repeated runs (e.g. while iterating on
        # `askr init` itself) restarted a perfectly healthy daemon every time,
        # wiping its in-memory trigger/dedup state for no reason.
        existing_plist = ""
        if os.path.exists(plist_path):
            with open(plist_path) as f:
                existing_plist = f.read()

        if existing_plist == plist:
            from askr.session.lifecycle import daemon_is_running
            if daemon_is_running():
                return True, plist_path

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

    # architecture.md gets generated from the codebase; implementation log is
    # per-developer JSONL, populated incrementally — neither uses a template.
    # only fall back to template if generation fails
    template_only_files = {
        f"handover_{developer}.md": "handover_template.md",
        "blockers.md":              "blockers_template.md",
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

    # Per-developer task queue (JSONL — one task per line, union-merge safe)
    tasks_dir = state_path("tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    queue_path = os.path.join(tasks_dir, f"queue_{developer}.jsonl")
    if not os.path.exists(queue_path):
        open(queue_path, "w").close()
        created.append(f"tasks/queue_{developer}.jsonl")

    # Shared goals store (JSONL — append-only, union-merge safe)
    goals_path = state_path("goals.jsonl")
    if not os.path.exists(goals_path):
        open(goals_path, "w").close()
        created.append("goals.jsonl")

    # Per-developer implementation log (JSONL — file/command actions, union-merge safe)
    impl_path = state_path(f"implementation_{developer}.jsonl")
    if not os.path.exists(impl_path):
        open(impl_path, "w").close()
        created.append(f"implementation_{developer}.jsonl")

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
        from askr.state.writer import update_architecture, append_implementation_entry

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

            with console.status("  generating architecture.md from codebase...", spinner="dots"):
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

        # Seed implementation_<dev>.jsonl with what's already built, as baseline entries
        impl_path = state_path(f"implementation_{developer}.jsonl")
        if not os.path.exists(impl_path) or os.path.getsize(impl_path) == 0:
            top_files = sorted(snapshot, key=lambda x: x.get("_score", 0), reverse=True)[:25]
            for e in top_files:
                if e.get("file") and e.get("purpose"):
                    append_implementation_entry("baseline", f"{e['file']} - {e['purpose']}", developer)
            console.print(f"  [green]✓[/green] [dim]implementation_{developer}.jsonl - seeded from snapshot[/dim]")
        else:
            console.print(f"  [dim]- skipped implementation_{developer}.jsonl (already exists)[/dim]")

        return True

    except Exception as e:
        console.print(f"  [yellow]⚠ snapshot generation failed: {e}[/yellow]")
        return False


def _create_fallback_generated_files(developer: str):
    templates_dir = os.path.join(ASKR_DIR, "askr", "state", "templates")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for target, template in [
        ("architecture.md", "architecture_template.md"),
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

    impl_path = state_path(f"implementation_{developer}.jsonl")
    if not os.path.exists(impl_path):
        open(impl_path, "w").close()


def _update_gitignore():
    gitignore = ".gitignore"
    entries = [
        ".llm_snapshot/",
        ".askr_log",
        "askr_state/architecture.md",
        "askr_state/project_brief.md",
        "askr_state/notifications.log",
    ]
    existing = ""
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            existing = f.read()
    additions = [e for e in entries if e not in existing]
    if additions:
        with open(gitignore, "a") as f:
            f.write("\n# askr\n" + "\n".join(additions) + "\n")


def _install_gitattributes():
    """Write union-merge rules for append-only shared state files."""
    rules = [
        "askr_state/decisions.jsonl    merge=union",
        "askr_state/goals.jsonl        merge=union",
        "askr_state/failed_approaches.md merge=union",
        "askr_state/tasks/queue_*.jsonl merge=union",
        "askr_state/implementation_*.jsonl merge=union",
    ]
    ga_path = ".gitattributes"
    existing = ""
    if os.path.exists(ga_path):
        with open(ga_path) as f:
            existing = f.read()
    additions = [r for r in rules if r.split()[0] not in existing]
    if additions:
        with open(ga_path, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("# askr — append-only files use union merge to prevent concurrent-push conflicts\n")
            f.write("\n".join(additions) + "\n")
        return True
    return False


def _register_team_member(developer: str):
    """Add developer to askr_state/team.json roster. Creates file if missing."""
    try:
        team_path = state_path("team.json")
        roster = {"members": []}
        if os.path.exists(team_path):
            with open(team_path) as f:
                roster = json.load(f)
        if developer not in roster.get("members", []):
            roster.setdefault("members", []).append(developer)
            with open(team_path, "w") as f:
                json.dump(roster, f, indent=2)
    except Exception:
        pass


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

    # Ensure API keys are configured globally before doing anything that needs them
    from askr.utils import env as _env
    _env.load()
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("  [yellow]no API keys found — let's set them up[/yellow]")
        console.print()
        from askr.cli.ask import setup_keys
        setup_keys()
        _env.load()

    # Register developer in team roster
    _register_team_member(developer)

    # Create session-specific files from templates
    created, skipped = _create_skeleton_files(developer)
    for f in created:
        console.print(f"  [green]✓[/green] created  [dim]{f}[/dim]")
    for f in skipped:
        console.print(f"  [dim]- skipped {f} (already exists)[/dim]")

    # Mark log position before any API calls so we can tally init cost at the end
    try:
        from askr.utils.logger import log_line_mark, cost_since_mark
        _init_log_mark = log_line_mark()
    except Exception:
        _init_log_mark = None

    # Generate architecture.md and implementation_<dev>.jsonl from codebase snapshot
    if not os.path.exists(SNAPSHOT_PATH):
        console.print()
        with console.status("  indexing codebase...", spinner="dots"):
            try:
                from askr.qa.snapshot import build_snapshot
                build_snapshot(show_progress=False)
            except Exception as e:
                console.print(f"  [yellow]⚠ snapshot failed: {e}[/yellow]")
        if os.path.exists(SNAPSHOT_PATH):
            console.print("  [green]✓[/green] codebase indexed")
        else:
            console.print("  [yellow]⚠ indexing failed — architecture.md will use template[/yellow]")

    if os.path.exists(SNAPSHOT_PATH):
        generated = _generate_architecture_from_snapshot(developer)
        if not generated:
            _create_fallback_generated_files(developer)
    else:
        _create_fallback_generated_files(developer)

    console.print()

    _install_hooks()
    for event in HOOK_MAP:
        console.print(f"  [green]✓[/green] hook  [dim]{event}[/dim]")

    new_tools, _ = _install_allowed_tools()
    tools_list = ", ".join(sorted(set(BASELINE_ALLOWED_TOOLS)))
    if new_tools:
        console.print(f"  [green]✓[/green] allowedTools  [dim]{tools_list}[/dim]")
    else:
        console.print(f"  [dim]- allowedTools already configured ({tools_list})[/dim]")

    claude_md_result = _install_claude_md()
    if claude_md_result == "created":
        console.print("  [green]✓[/green] CLAUDE.md  [dim]created with behavioral instructions[/dim]")
    elif claude_md_result == "updated":
        console.print("  [green]✓[/green] CLAUDE.md  [dim]behavioral section updated[/dim]")
    else:
        console.print("  [dim]- CLAUDE.md  behavioral section already up to date[/dim]")

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

    # Claude CLI check — required for autonomous session restarts
    import shutil as _shutil
    if _shutil.which("claude"):
        console.print("  [green]✓[/green] claude CLI  [dim](autonomous restarts enabled)[/dim]")
    else:
        console.print()
        console.print("  [red]✗ claude CLI not found[/red]  — autonomous session restarts will be disabled")
        console.print("  [dim]  Install it to enable hands-free context/quota cycling:[/dim]")
        console.print("  [bold]  npm install -g @anthropic-ai/claude-code[/bold]")
        console.print("  [dim]  Then re-run[/dim] [bold]askr init[/bold] [dim]to verify.[/dim]")

    power = _power_source()
    if power == "battery":
        console.print()
        console.print("  [yellow]⚠ on battery[/yellow]  [dim]— caffeinate cannot prevent sleep if lid is closed.")
        console.print("  [dim]  Plug in for reliable overnight runs.[/dim]")

    console.print()
    _update_gitignore()
    if _install_gitattributes():
        console.print("  [green]✓[/green] .gitattributes [dim](union merge on shared state files)[/dim]")
    else:
        console.print("  [dim]- .gitattributes already configured[/dim]")

    console.print("  [dim]state files:[/dim] [bold]askr_state/[/bold]")
    console.print("  [dim]commit askr_state/ to git so your team shares the same ground truth[/dim]")
    console.print()

    # Load .env from the askr repo dir directly — env.load() may not have found it
    # if the user ran `askr init` from a different directory.
    from dotenv import load_dotenv as _load_dotenv
    _askr_dot_env = os.path.join(ASKR_DIR, ".env")
    if os.path.exists(_askr_dot_env):
        _load_dotenv(dotenv_path=_askr_dot_env, override=False)

    from askr.state.config import load_project_config, save_project_config

    # A webhook URL isn't a secret in the shoulder-surfing sense getpass() protects
    # against — and getpass() hides all input including paste, which repeatedly
    # looked like a hang to users pasting a long Discord URL here (see
    # askr_state/failed_approaches.md, 2026-06-15).
    #
    # Per-project webhook (overrides global) — stored locally in askr_state/config.json,
    # which is gitignored. Never committed: it's a plaintext secret, and each teammate
    # should set their own (or share it out of band, e.g. 1Password/DM).
    existing_project_hook = load_project_config().get("discord_webhook", "")
    console.print()
    console.print(f"  [dim]project Discord webhook (current: {'set' if existing_project_hook else 'none'})[/dim]")
    try:
        project_hook = input("  project webhook (enter to keep/skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        project_hook = ""
    if project_hook:
        save_project_config({"discord_webhook": project_hook})
        console.print("  [green]✓[/green] project webhook saved to askr_state/config.json [dim](gitignored, not synced to teammates)[/dim]")
    elif existing_project_hook:
        console.print("  [dim]- project webhook unchanged[/dim]")

    # Global fallback webhook — stored in ~/.config/askr/.env
    if not existing_project_hook and not project_hook and not os.getenv("ASKR_DISCORD_WEBHOOK"):
        console.print("  [dim]no global webhook set — enter one as fallback (enter to skip)[/dim]")
        try:
            global_hook = input("  global webhook: ").strip()
        except (KeyboardInterrupt, EOFError):
            global_hook = ""
        if global_hook:
            config_dir = os.path.expanduser("~/.config/askr")
            env_file = os.path.join(config_dir, ".env")
            os.makedirs(config_dir, exist_ok=True)
            with open(env_file, "a") as _f:
                _f.write(f"\nASKR_DISCORD_WEBHOOK={global_hook}\n")
            os.chmod(env_file, 0o600)  # contains plaintext keys/webhook — default umask leaves this world-readable
            os.environ["ASKR_DISCORD_WEBHOOK"] = global_hook
            console.print("  [green]✓[/green] global webhook saved to ~/.config/askr/.env")

    # Voice notifications — machine-level preference (native macOS `say`), not
    # per-project: it's "does this Mac talk", same trait as the developer name.
    if platform.system() == "Darwin":
        from askr.state.config import (
            load_voice_enabled, save_voice_enabled,
            load_voice_mode, save_voice_mode,
            load_voice_single, save_voice_single,
            load_voice_prefix, load_voice_body, save_voice_style,
        )
        existing_voice = load_voice_enabled()
        console.print()
        console.print(f"  [dim]voice notifications (current: {'on' if existing_voice else 'off'})[/dim]")
        try:
            voice_raw = input("  enable spoken updates via macOS `say`? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            voice_raw = ""
        if voice_raw == "y":
            save_voice_enabled(True)
            console.print("  [green]✓[/green] voice notifications enabled")
        elif voice_raw == "n":
            save_voice_enabled(False)

        if voice_raw == "y" or (existing_voice and voice_raw != "n"):
            console.print(f"  [dim]voice style (current: {load_voice_mode()})[/dim]")
            try:
                mode_raw = input("  one voice for everything, or a two-voice sonic logo? [1=single/2=dual, enter to keep]: ").strip()
            except (KeyboardInterrupt, EOFError):
                mode_raw = ""
            if mode_raw == "1":
                save_voice_mode("single")
                try:
                    voice_name = input(f"  which voice? (current: {load_voice_single()}, enter to keep): ").strip()
                except (KeyboardInterrupt, EOFError):
                    voice_name = ""
                if voice_name:
                    save_voice_single(voice_name)
                console.print("  [green]✓[/green] single-voice mode saved")
            elif mode_raw == "2":
                save_voice_mode("dual")
                try:
                    prefix_voice = input(f"  prefix voice? (current: {load_voice_prefix()}, enter to keep): ").strip()
                    body_voice = input(f"  body voice? (current: {load_voice_body()}, enter to keep): ").strip()
                except (KeyboardInterrupt, EOFError):
                    prefix_voice = body_voice = ""
                save_voice_style(prefix_voice or load_voice_prefix(), body_voice or load_voice_body())
                console.print("  [green]✓[/green] dual-voice sonic logo saved")

    from askr.clients.discord import _get_webhook_url
    if _get_webhook_url():
        try:
            from askr.clients.discord import send_message
            from askr.clients.claude import call_claude
            from askr.qa.context_loader import load_inventory

            repo_name = os.path.basename(os.getcwd())
            brief = ""
            if os.path.exists(SNAPSHOT_PATH):
                inventory = load_inventory()
                with console.status("  generating repo brief for Discord...", spinner="dots"):
                    brief = call_claude(
                        "You write concise technical onboarding briefs.",
                        f"In 5 bullet points, describe what this codebase is, what's built, "
                        f"and what looks in-progress. Be factual and specific. No fluff.\n\nFILES:\n{inventory}",
                        mode="default",
                        query_preview="onboarding brief"
                    )

            welcome = f"**[askr] {developer} is online** — `{repo_name}`"
            if brief:
                welcome += f"\n\n**Repo brief:**\n{brief.strip()}"
            sent, err = send_message(welcome)
            if sent and brief:
                console.print("  [green]✓[/green] repo brief posted to Discord")
            elif not sent:
                console.print(f"  [yellow]⚠ Discord send failed[/yellow] — {err}")
        except Exception as e:
            console.print(f"  [yellow]⚠ Discord error:[/yellow] {e}")

    if _init_log_mark is not None:
        init_cost = cost_since_mark(_init_log_mark)
        if init_cost > 0:
            console.print(f"  [dim]init cost[/dim]  [green]${init_cost:.4f}[/green]")

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


_RESUMED_PATH = os.path.expanduser("~/.config/askr/resumed.json")


def _pop_resumed_marker() -> dict:
    """Read and delete the resumed marker if present."""
    try:
        if not os.path.exists(_RESUMED_PATH):
            return {}
        with open(_RESUMED_PATH) as f:
            data = json.load(f)
        os.remove(_RESUMED_PATH)
        return data
    except Exception:
        return {}


def _statusline_text() -> str:
    """Compact one-line output for 'askr status --line'."""
    try:
        resumed = _pop_resumed_marker()
        if resumed:
            from askr.state.analytics import _fmt
            saved = resumed.get("saved_seconds", 0)
            saved_str = f" saved:{_fmt(saved)}" if saved else ""
            return f"askr ↺ Resumed{saved_str}"

        if not os.path.exists(_stats_path()):
            return "askr ·"
        with open(_stats_path()) as f:
            s = json.load(f)

        ctx_pct   = int(round(s.get("context_pct", 0) * 100))
        ctx_label = s.get("context_label", "ok")
        quota_pct = s.get("quota_pct")
        reset_at  = s.get("quota_reset_at", "")

        # session_start.py writes this file immediately on startup with
        # turns=0 so a same-session fallback never lands on a stale sibling
        # session's stats — but that means "ctx:0%" before the first message
        # looks like a measured reading instead of "no usage data yet".
        # Distinguish the two.
        ctx_part   = f"ctx:{ctx_pct}%" if s.get("turns", 0) > 0 else "ctx:–"
        quota_part = f"quota:{quota_pct:.0f}%" if quota_pct is not None else ""
        reset_part = _reset_countdown(reset_at) if reset_at else ""

        label_suffix = {"checkpoint": " ⚠", "near limit": " !"}
        quota_warn   = " ⚠" if quota_pct is not None and quota_pct >= 90 else (
                       " !" if quota_pct is not None and quota_pct >= 80 else "")
        suffix = label_suffix.get(ctx_label, "") or quota_warn

        parts = ["askr", ctx_part]
        if quota_part:
            parts.append(quota_part)
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
        import shutil as _shutil
        if _shutil.which("claude"):
            console.print(f"  [dim]claude CLI[/dim]  [green]found[/green]  [dim](autonomous restarts enabled)[/dim]")
        else:
            console.print(f"  [dim]claude CLI[/dim]  [red]not found[/red]  [dim]— install: npm install -g @anthropic-ai/claude-code[/dim]")
        has_behavioral = (
            os.path.exists("CLAUDE.md") and
            _CLAUDE_MD_MARKER_START in open("CLAUDE.md").read()
        )
        console.print(f"  [dim]CLAUDE.md[/dim]   {'[green]behavioral instructions active[/green]' if has_behavioral else '[yellow]missing — run askr init[/yellow]'}")

    if os.path.exists(_stats_path()):
        try:
            import time as _time
            stats_age = _time.time() - os.path.getmtime(_stats_path())
            with open(_stats_path()) as f:
                s = json.load(f)
            console.print()
            if stats_age > 600:
                console.print(f"  [dim]context[/dim]     [dim]no active session[/dim]")
            else:
                ctx_pct    = int(round(s.get("context_pct", 0) * 100))
                ctx_tokens = s.get("context_tokens", 0)
                ctx_window = s.get("context_window", 200000)
                ctx_label  = s.get("context_label", "ok")
                label_map  = {"high": "[yellow]high[/yellow]", "near limit": "[red]near limit[/red]", "checkpoint": "[bold red]checkpoint[/bold red]"}
                label_str  = f"  {label_map[ctx_label]}" if ctx_label in label_map else ""
                console.print(f"  [dim]context[/dim]     [bold]{ctx_pct}%[/bold] ({ctx_tokens:,} / {ctx_window:,} — this chat only){label_str}")

            quota_pct  = s.get("quota_pct")
            reset_at   = s.get("quota_reset_at", "")
            q7d        = s.get("quota_7d_pct")
            if quota_pct is not None:
                countdown = _reset_countdown(reset_at) if reset_at else ""
                q_color   = "bold red" if quota_pct >= 90 else ("yellow" if quota_pct >= 80 else "bold")
                q7d_str   = f"  [dim]7d: {q7d:.0f}%[/dim]" if q7d is not None else ""
                reset_str = f"  [dim]{countdown}[/dim]" if countdown else ""
                console.print(f"  [dim]quota (5h)[/dim]  [{q_color}]{quota_pct:.0f}%[/{q_color}]{q7d_str}{reset_str}")
            elif reset_at:
                countdown = _reset_countdown(reset_at)
                console.print(f"  [dim]quota reset[/dim]  {countdown}")
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


def _maybe_launch_for_goal(goal_text: str):
    """Start an autonomous Claude session for this goal immediately."""
    try:
        from askr.session.lifecycle import (
            _claude_cli_available, _start_claude, _write_launch_mode,
        )

        if not _claude_cli_available():
            console.print("  [yellow]warn:[/yellow] claude not in PATH — start it manually\n")
            return

        # Always use cwd — never the stored global project path.
        # Running `askr goal add` in /askr should launch in /askr, not whatever
        # repo last ran `askr init`.
        project_path = os.getcwd()
        _write_launch_mode(goal_text)
        _start_claude(project_path, initial_prompt=f"Read the handover and work on this goal autonomously: {goal_text}")
        console.print("  [green]→[/green] starting autonomous session for this goal\n")
    except Exception:
        pass


def cmd_goal(args: list[str]):
    from askr.state.goals import add_goal, complete_goal, discard_goal

    if not args:
        console.print("\n  [bold]askr goal[/bold]")
        console.print("  [dim]askr goal add \"finish the auth layer\"[/dim]")
        console.print("  [dim]askr goal add \"ship phase 2\" --backlog[/dim]")
        console.print("  [dim]askr goal add \"finish the auth layer\" --launch[/dim]  [dim](also starts an autonomous Claude session on it now)[/dim]")
        console.print("  [dim]askr goal done \"finish the auth layer\"[/dim]")
        console.print("  [dim]askr goal discard \"finish the auth layer\"[/dim]\n")
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

        # Adding a goal only records it. Launching an autonomous, unsandboxed
        # Claude session on it is a much bigger action and must be opted into
        # explicitly with --launch — it used to fire unconditionally for any
        # today-goal, with no confirmation and no mention of it in --help.
        if section == "today" and "--launch" in args:
            _maybe_launch_for_goal(text)

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

    elif sub == "discard":
        if len(args) < 2:
            console.print("\n  [red]usage: askr goal discard \"goal text\"[/red]\n")
            return
        text = args[1]
        if discard_goal(text):
            console.print(f"\n  [yellow]✓[/yellow] discarded: [bold]{text}[/bold]\n")
        else:
            console.print(f"\n  [yellow]not found:[/yellow] {text}\n")
            console.print("  [dim]run[/dim] [bold]askr goals[/bold] [dim]to see open goals[/dim]\n")

    else:
        console.print(f"\n  [yellow]unknown: askr goal {sub}[/yellow]")
        console.print("  [dim]use: add / done / discard[/dim]\n")


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

    if os.path.exists(_stats_path()):
        console.print(f"  [dim]session:[/dim] {_statusline_text()}")

    allowed = _load_claude_settings().get("allowedTools", [])
    if allowed:
        console.print(f"  [dim]pre-approved ({len(allowed)}):[/dim] {', '.join(sorted(allowed))}")
    else:
        console.print("  [yellow]⚠ no tools pre-approved[/yellow]  [dim]— run askr init[/dim]")

    console.print()
    console.print(f"  [dim]log:[/dim] {log_path}")
    console.print(f"  [dim]stop:[/dim] [bold]askr launch --stop[/bold]")
    console.print()


def cmd_uninstall(global_uninstall: bool = False):
    """
    Default (project-scoped): undo askr's integration with THIS repo only —
    hooks/statusLine in .claude/settings.json, and optionally askr_state/.
    Leaves the daemon, ~/.config/askr/, and the IDE extension untouched,
    since those are machine-wide and shared by every other askr project
    on this machine.

    --global: also tears down the machine-wide install (daemon, identity,
    keys, IDE extension). Affects every askr project on this machine —
    until askr ships via brew, this is the closest equivalent to
    `brew uninstall askr`.
    """
    import shutil as _shutil
    import subprocess as _sp

    console.print()
    if global_uninstall:
        console.rule("[bold red]askr uninstall --global[/]", style="red")
        console.print("  [dim]removing the machine-wide install — affects every askr project on this machine[/dim]")
    else:
        console.rule("[bold red]askr uninstall[/]", style="red")
        console.print("  [dim]removing askr from this repo only — use --global to remove it from this machine[/dim]")
    console.print()

    if global_uninstall:
        # 1. Launchd daemon — machine-wide, watches every askr project
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.askr.daemon.plist")
        if os.path.exists(plist_path):
            _sp.run(["launchctl", "unload", plist_path], capture_output=True)
            os.remove(plist_path)
            console.print("  [green]✓[/green] launchd daemon unloaded and plist removed")
        else:
            console.print("  [dim]- launchd plist not found (already removed)[/dim]")

        try:
            from askr.session.lifecycle import stop_daemon
            if stop_daemon():
                console.print("  [green]✓[/green] daemon process stopped")
        except Exception:
            pass

    # Claude Code hooks + statusLine — project-local, always safe to remove
    if os.path.exists(CLAUDE_SETTINGS):
        settings = _load_claude_settings()
        changed = False

        # Remove hooks that point to askr
        hooks = settings.get("hooks", {})
        for event in list(hooks.keys()):
            original = hooks[event]
            filtered = [
                group for group in original
                if not any(
                    "askr" in h.get("command", "").lower()
                    for h in group.get("hooks", [])
                )
            ]
            if filtered != original:
                hooks[event] = filtered
                changed = True
            if not hooks[event]:
                del hooks[event]
                changed = True

        # Remove statusLine if it points to askr
        sl = settings.get("statusLine", {})
        if "askr" in sl.get("command", "").lower():
            del settings["statusLine"]
            changed = True

        if changed:
            _save_claude_settings(settings)
            console.print("  [green]✓[/green] hooks and statusLine removed from .claude/settings.json")
        else:
            console.print("  [dim]- no askr hooks found in .claude/settings.json[/dim]")

    if global_uninstall:
        # Askr config/state directory — identity, keys, cost history; shared machine-wide
        askr_config = os.path.expanduser("~/.config/askr")
        if os.path.isdir(askr_config):
            _shutil.rmtree(askr_config)
            console.print(f"  [green]✓[/green] removed ~/.config/askr/")
        else:
            console.print("  [dim]- ~/.config/askr/ not found[/dim]")

        # IDE extension — editor-wide install, not per-repo
        ext_name = "askr.askr-status-1.0.0"
        for ext_base in [os.path.expanduser("~/.cursor/extensions"), os.path.expanduser("~/.vscode/extensions")]:
            ext_path = os.path.join(ext_base, ext_name)
            if os.path.isdir(ext_path):
                _shutil.rmtree(ext_path)
                ide = "Cursor" if "cursor" in ext_base else "VS Code"
                console.print(f"  [green]✓[/green] removed IDE extension from {ide}")

    # Optionally remove askr_state/ — project-local, always prompted
    state_dir = get_state_dir()
    if os.path.isdir(state_dir):
        console.print()
        console.print(f"  [yellow]askr_state/[/yellow] exists at [dim]{state_dir}[/dim]")
        console.print("  [dim]This contains your project state files (handover, architecture, goals).[/dim]")
        try:
            raw = input("  Remove askr_state/ too? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            raw = "n"
        if raw == "y":
            _shutil.rmtree(state_dir)
            console.print(f"  [green]✓[/green] removed {state_dir}")
        else:
            console.print("  [dim]kept askr_state/ — remove manually if needed[/dim]")

    console.print()
    if global_uninstall:
        console.print("  [green]done[/green] — askr fully removed from this machine\n")
    else:
        console.print("  [green]done[/green] — askr removed from this repo [dim](daemon and global config left intact — use --global to remove those too)[/dim]\n")


def _load_pending_tasks(dev: str) -> list:
    """Read pending tasks from queue_<dev>.jsonl. Returns list of task dicts."""
    path = os.path.join(get_state_dir(), "tasks", f"queue_{dev}.jsonl")
    if not os.path.exists(path):
        return []
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    tasks.append(json.loads(line))
                except Exception:
                    pass
    return tasks


def _queue_task_for(target_dev: str, description: str, from_dev: str, push: bool = True):
    """Append a task to target_dev's JSONL queue and optionally commit+push."""
    import subprocess as _sp
    import uuid as _uuid

    state_dir  = get_state_dir()
    tasks_dir  = os.path.join(state_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    queue_path = os.path.join(tasks_dir, f"queue_{target_dev}.jsonl")

    entry = json.dumps({
        "id":   _uuid.uuid4().hex[:8],
        "desc": description.strip(),
        "from": from_dev,
        "at":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    from askr.state.writer import file_lock
    with file_lock(queue_path):
        with open(queue_path, "a") as f:
            f.write(entry + "\n")

    if not push:
        return True

    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        _sp.run(["git", "add", queue_path], capture_output=True)
        _sp.run(
            ["git", "commit", "-m", f"askr: task queued for {target_dev} [{from_dev}] {ts}"],
            capture_output=True,
        )
        result = _sp.run(["git", "push", "--quiet"], capture_output=True, timeout=30)
        if result.returncode == 0:
            console.print(f"\n  [green]✓[/green] queued for [bold]{target_dev}[/bold]: {description}")
            console.print(f"  [dim]pushed — {target_dev} will receive it at next session start[/dim]\n")
        else:
            console.print(f"\n  [green]✓[/green] queued for [bold]{target_dev}[/bold]: {description}")
            console.print(f"  [yellow]⚠ push failed — run git push manually[/yellow]\n")
        return True
    except Exception as e:
        console.print(f"\n  [yellow]⚠ commit/push failed: {e}[/yellow]\n")
        return False


def _approve_held_tasks(dev: str) -> bool:
    """Write the one-shot flag session_start.py checks — lets the next
    SessionStart drain the queue even though the session is still dangerous.
    Doesn't touch the queue file itself; draining happens at session start."""
    tasks_dir = os.path.join(get_state_dir(), "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    flag_path = os.path.join(tasks_dir, f"approved_{dev}.flag")
    with open(flag_path, "w") as f:
        f.write(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    return True


def _discard_held_tasks(dev: str) -> int:
    """Drain the queue straight to discarded_<dev>.jsonl without ever
    injecting it into a session. Same lock as the queue writer/drainer —
    without it a task appended mid-discard would be silently lost."""
    from askr.state.writer import file_lock

    tasks_dir     = os.path.join(get_state_dir(), "tasks")
    queue_path    = os.path.join(tasks_dir, f"queue_{dev}.jsonl")
    discard_path  = os.path.join(tasks_dir, f"discarded_{dev}.jsonl")

    if not os.path.exists(queue_path):
        return 0

    with file_lock(queue_path):
        tasks = []
        with open(queue_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        tasks.append(json.loads(line))
                    except Exception:
                        pass
        if not tasks:
            return 0

        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(discard_path, "a") as f:
            for t in tasks:
                t["discarded_at"] = ts
                f.write(json.dumps(t) + "\n")

        open(queue_path, "w").close()
    return len(tasks)


def cmd_task(args: list):
    """
    askr task queue <dev> "description"  — add a task to a developer's queue
    askr task list [<dev>]               — show pending tasks for a developer
    askr task approve <dev>              — release tasks held by the permission gate
    askr task discard <dev>              — drop tasks held by the permission gate
    """
    import subprocess as _sp
    import uuid as _uuid

    sub = args[0] if args else ""

    if sub == "queue":
        if len(args) < 3:
            console.print("\n  usage: [bold]askr task queue <developer> \"task description\"[/bold]\n")
            return
        target_dev  = args[1]
        description = " ".join(args[2:])
        _queue_task_for(target_dev, description, from_dev=load_developer())

    elif sub == "list":
        target_dev = args[1] if len(args) > 1 else load_developer()
        tasks = _load_pending_tasks(target_dev)

        if not tasks:
            console.print(f"\n  [dim]{target_dev}: no pending tasks[/dim]\n")
            return

        held = False
        if target_dev == load_developer():
            try:
                from askr.session.permission_gate import is_dangerous_session
                held, reasons = is_dangerous_session(os.path.dirname(get_state_dir()))
            except Exception:
                held, reasons = False, []

        console.print(f"\n  [bold]{target_dev}[/bold] — {len(tasks)} pending task(s):\n")
        for t in tasks:
            console.print(f"  • [{t.get('from','?')}] {t['desc']}")
        if held:
            console.print(f"\n  [yellow]held[/yellow] — session has {'; '.join(reasons)}")
            console.print(f"  [dim]askr task approve {target_dev}[/dim]  or  [dim]askr task discard {target_dev}[/dim]")
        console.print()

    elif sub == "approve":
        target_dev = args[1] if len(args) > 1 else load_developer()
        tasks = _load_pending_tasks(target_dev)
        _approve_held_tasks(target_dev)
        console.print(f"\n  [green]✓[/green] approved — {len(tasks)} task(s) for [bold]{target_dev}[/bold] will load at next session start\n")

    elif sub == "discard":
        target_dev = args[1] if len(args) > 1 else load_developer()
        n = _discard_held_tasks(target_dev)
        if n:
            console.print(f"\n  [green]✓[/green] discarded {n} task(s) for [bold]{target_dev}[/bold]\n")
        else:
            console.print(f"\n  [dim]{target_dev}: no pending tasks to discard[/dim]\n")

    else:
        console.print("\n  usage:")
        console.print("    [bold]askr task queue <dev> \"description\"[/bold]  — queue a task for a developer")
        console.print("    [bold]askr task list [<dev>][/bold]               — show pending tasks")
        console.print("    [bold]askr task approve [<dev>][/bold]            — release tasks held by the permission gate")
        console.print("    [bold]askr task discard [<dev>][/bold]            — drop tasks held by the permission gate\n")


def cmd_team():
    """Show all developers' current state from their handover JSONs."""
    state_dir = get_state_dir()
    if not os.path.isdir(state_dir):
        console.print("\n  [yellow]no askr_state/ found — run askr init first[/yellow]\n")
        return

    import glob as _glob

    handover_files = _glob.glob(os.path.join(state_dir, "handover_*.json"))
    if not handover_files:
        console.print("\n  [dim]no developer handovers found[/dim]\n")
        return

    # Load stats for live context %
    stats_by_project: dict = {}
    try:
        from askr.session.lifecycle import _read_all_stats
        for s in _read_all_stats():
            pp = s.get("project_path", "")
            if pp:
                stats_by_project[pp] = s
    except Exception:
        pass

    try:
        from askr.session.monitor import find_project_root
        current_project = find_project_root()
    except Exception:
        current_project = os.getcwd()

    from datetime import timezone as _tz, timedelta as _td

    console.print()
    console.print("  [bold]team[/bold]\n")

    for hf in sorted(handover_files):
        dev = os.path.basename(hf).replace("handover_", "").replace(".json", "")
        try:
            with open(hf) as f:
                h = json.load(f)
        except Exception:
            continue

        task        = h.get("task", "—")[:60]
        blockers    = h.get("blockers", [])
        ts_str      = h.get("session_metadata", {}).get("timestamp", "")
        next_acts   = h.get("next_actions", [])
        next_action = next_acts[0].get("action", "")[:55] if next_acts else "—"

        # Time since last session
        last_seen = "unknown"
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                delta = datetime.now(_tz.utc) - ts
                secs = delta.total_seconds()
                if secs < 0:
                    last_seen = "active now"
                elif secs < 3600:
                    last_seen = f"{int(secs // 60)}m ago"
                elif secs < 86400:
                    last_seen = f"{int(secs // 3600)}h ago"
                else:
                    last_seen = f"{delta.days}d ago"
            except Exception:
                pass

        # Live context % — match stats to this dev's last known project
        dev_project = h.get("session_metadata", {}).get("project_path", current_project)
        stats = stats_by_project.get(dev_project) or stats_by_project.get(current_project, {})
        ctx_pct = stats.get("context_pct")
        ctx_str = f"ctx:{ctx_pct:.0%}" if ctx_pct else "idle"

        blocker_str = f"  [red]⚠ {blockers[0][:50]}[/red]" if blockers else ""

        console.print(f"  [bold]{dev:<12}[/bold] [dim]{ctx_str:<10}[/dim] last: {last_seen}")
        console.print(f"  [dim]  task:[/dim] {task}")
        console.print(f"  [dim]  next:[/dim] {next_action}")
        if blocker_str:
            console.print(blocker_str)

        # Pending tasks in queue
        pending = _load_pending_tasks(dev)
        if pending:
            console.print(f"  [yellow]  {len(pending)} queued task(s)[/yellow]")

        console.print()


def cmd_report():
    """Send a morning/daily report to Discord as a PNG card, print summary to stdout."""
    from askr.state.analytics import today_summary, _load_all
    from askr.state.goals import load_today_goals, load_open_goals
    from askr.session.cost import today_cost_summary
    from datetime import datetime as _dt

    developer = load_developer()
    today = _dt.now().strftime("%Y-%m-%d")

    summary      = today_summary()
    cost_today   = today_cost_summary()
    open_goals   = load_open_goals() or []
    today_goals  = load_today_goals() or []
    done_today   = [g.lstrip("[x] ✓ ").strip() for g in today_goals
                    if g.startswith("[x]") or "✓" in g]

    console.print()
    console.print(f"[bold]Daily Report — {developer} — {today}[/bold]")
    if summary["sessions"] > 0:
        console.print(f"  Sessions: {summary['sessions']}  |  Time saved: {summary['total_human']}")
    if cost_today:
        console.print(
            f"  Cost: ${cost_today.get('total_cost_usd', 0):.2f}  |  "
            f"Saved: ${cost_today.get('total_savings_usd', 0):.2f}"
        )
    if done_today:
        console.print("  Completed: " + ", ".join(done_today[:3]))
    if open_goals:
        console.print("  Open: " + ", ".join(open_goals[:3]))
    console.print()

    # Try to send a PNG morning report card
    discord_ok = False
    try:
        from askr.session.report_image import morning_report_card
        from askr.clients.discord import send_file, send_message

        img_path = morning_report_card(
            date=today,
            sessions=summary.get("sessions", 0),
            total_seconds=summary.get("total_seconds", 0),
            total_cost_usd=cost_today.get("total_cost_usd", 0.0),
            total_savings_usd=cost_today.get("total_savings_usd", 0.0),
            total_tokens=cost_today.get("total_tokens", 0),
            goals_completed=done_today,
            goals_open=open_goals[:4],
        )

        caption = f"**[askr] Daily Report — {developer} — {today}**"
        if img_path:
            discord_ok = send_file(img_path, caption)
            try:
                os.remove(img_path)
            except Exception:
                pass

        if not discord_ok:
            # text fallback
            lines = [caption]
            if summary["sessions"] > 0:
                lines.append(f"Sessions: {summary['sessions']}  |  Time: {summary['total_human']}")
            if done_today:
                lines.extend(f"✓ {g}" for g in done_today)
            if open_goals:
                lines.extend(f"- {g}" for g in open_goals[:4])
            discord_ok, _ = send_message("\n".join(lines))

    except Exception as e:
        console.print(f"  [yellow]Report image failed:[/yellow] {e}")

    if discord_ok:
        console.print("  [green]✓[/green] sent to Discord")
    else:
        console.print("  [yellow]Discord webhook not configured[/yellow] — set ASKR_DISCORD_WEBHOOK in .env")


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
        console.print("  [dim]askr uninstall           - remove askr from this repo only[/dim]")
        console.print("  [dim]askr uninstall --global  - remove askr from this whole machine[/dim]")
        console.print("  [dim]askr report              - send morning/daily report to Discord[/dim]")
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
    elif cmd == "uninstall":
        cmd_uninstall(global_uninstall="--global" in rest or "--everywhere" in rest)
    elif cmd == "report":
        cmd_report()
    elif cmd == "task":
        cmd_task(rest)
    elif cmd == "team":
        cmd_team()
    else:
        console.print(f"\n  [yellow]askr {cmd}[/yellow] [dim]- not yet implemented, see roadmap.md[/dim]\n")


if __name__ == "__main__":
    main()
