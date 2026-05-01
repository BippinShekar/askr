#!/usr/bin/env python3

import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run
from snapshot import build_snapshot
from logger import show_summary
from display import console, print_progress, print_init, print_response


def setup_keys():
    config_dir = os.path.expanduser("~/.config/askr")
    env_file = os.path.join(config_dir, ".env")

    console.print()
    console.rule("[bold]askr setup[/]", style="dim")

    if os.path.exists(env_file):
        console.print(f"  [dim]keys already saved at[/dim] {env_file}")
        console.print("  [dim]delete that file to reconfigure[/dim]\n")
        return

    console.print(f"  [dim]saving to[/dim] {env_file}\n")

    anthropic_key = getpass.getpass("  ANTHROPIC_API_KEY: ").strip()
    if not anthropic_key:
        console.print("  [red]✗ anthropic key required[/red]\n")
        raise SystemExit(1)

    openai_key = getpass.getpass("  OPENAI_API_KEY (optional — press enter to skip): ").strip()

    os.makedirs(config_dir, exist_ok=True)
    with open(env_file, "w") as f:
        f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")
        if openai_key:
            f.write(f"OPENAI_API_KEY={openai_key}\n")

    console.print("\n  [green]✓ saved[/green]  [dim]now run[/dim] [bold]ask init[/bold] [dim]in your project\n[/dim]")


def init_project():
    cwd = os.getcwd()

    skip = {"venv", "node_modules", ".git", "__pycache__", "dist", "build", ".llm_snapshot"}
    count = 0
    for _, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        count += sum(1 for f in files if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")))

    est_cost = count * 0.0012
    print_init(cwd, count, est_cost)
    build_snapshot(full=True)

    gitignore = os.path.join(cwd, ".gitignore")
    entries = [".llm_snapshot/", ".askr_history"]
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            existing = f.read()
        additions = [e for e in entries if e not in existing]
        if additions:
            with open(gitignore, "a") as f:
                f.write("\n# askr\n" + "\n".join(additions) + "\n")
            console.print(f"  [dim]added to .gitignore:[/dim] {', '.join(additions)}")

    console.print("\n  [dim]done — run[/dim] [bold]ask \"your question\"[/bold] [dim]to start[/dim]\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("\n  [bold]askr[/bold]  [dim]context-aware codebase Q&A[/dim]")
        console.print("\n  [dim]ask \"cto: your question\"[/dim]")
        console.print("  [dim]ask setup[/dim]")
        console.print("  [dim]ask init[/dim]")
        console.print("  [dim]ask snap[/dim]")
        console.print("  [dim]ask log[/dim]\n")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "setup":
        setup_keys()
    elif cmd == "init":
        init_project()
    elif cmd == "snap":
        print_progress("rebuilding snapshot...")
        build_snapshot(full=True)
        print_progress("done.")
    elif cmd == "log":
        show_summary()
    else:
        query = " ".join(sys.argv[1:])
        result, mode = run(query)
        print_response(result, mode)
