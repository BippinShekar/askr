#!/usr/bin/env python3

import sys
import os
import getpass

import anthropic
import openai

from askr.qa.pipeline import run
from askr.qa.snapshot import build_snapshot
from askr.utils.logger import show_summary
from askr.utils.display import console, print_progress, print_init, print_response


def _run_query(query: str):
    try:
        return run(query)
    except anthropic.AuthenticationError:
        console.print("\n  [bold red]✗ Anthropic rejected your API key[/bold red]")
        console.print("  run [bold]ask setup[/bold] to reconfigure it\n")
        raise SystemExit(1)
    except anthropic.PermissionDeniedError:
        console.print("\n  [bold red]✗ Anthropic denied this request — often an insufficient credit balance[/bold red]")
        console.print("  check your balance at [dim]console.anthropic.com[/dim]\n")
        raise SystemExit(1)
    except anthropic.RateLimitError:
        console.print("\n  [bold red]✗ rate limited by Anthropic — try again in a moment[/bold red]\n")
        raise SystemExit(1)
    except anthropic.APIConnectionError:
        console.print("\n  [bold red]✗ couldn't reach Anthropic — check your network connection[/bold red]\n")
        raise SystemExit(1)
    except anthropic.AnthropicError as e:
        console.print(f"\n  [bold red]✗ Anthropic API error:[/bold red] {e}\n")
        raise SystemExit(1)
    except openai.AuthenticationError:
        console.print("\n  [bold red]✗ OpenAI rejected your API key[/bold red]")
        console.print("  run [bold]ask setup[/bold] to reconfigure it\n")
        raise SystemExit(1)
    except openai.RateLimitError:
        console.print("\n  [bold red]✗ rate limited by OpenAI — often an insufficient credit balance or too many requests[/bold red]\n")
        raise SystemExit(1)
    except openai.APIConnectionError:
        console.print("\n  [bold red]✗ couldn't reach OpenAI — check your network connection[/bold red]\n")
        raise SystemExit(1)
    except openai.OpenAIError as e:
        console.print(f"\n  [bold red]✗ OpenAI API error:[/bold red] {e}\n")
        raise SystemExit(1)


def setup_keys():
    config_dir = os.path.expanduser("~/.config/askr")
    env_file = os.path.join(config_dir, ".env")

    console.print()
    console.rule("[bold]askr setup[/]", style="dim")

    # Only prompt for whatever's actually missing — the old code bailed out
    # entirely the moment the file existed at all, so a user who'd only ever
    # set an Anthropic key (or had a stale file with a blank webhook) could
    # never get prompted for OpenAI/Discord without manually deleting the file.
    existing = {}
    if os.path.exists(env_file):
        from dotenv import dotenv_values
        existing = {k: v for k, v in dotenv_values(env_file).items() if v}
        console.print(f"  [dim]existing config found at[/dim] {env_file}\n")
    else:
        console.print(f"  [dim]saving to[/dim] {env_file}\n")

    anthropic_key = existing.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        console.print("  [dim]- ANTHROPIC_API_KEY already set[/dim]")
    else:
        anthropic_key = getpass.getpass("  ANTHROPIC_API_KEY: ").strip()
        if not anthropic_key:
            console.print("  [red]✗ anthropic key required[/red]\n")
            raise SystemExit(1)

    openai_key = existing.get("OPENAI_API_KEY", "")
    if openai_key:
        console.print("  [dim]- OPENAI_API_KEY already set[/dim]")
    else:
        openai_key = getpass.getpass("  OPENAI_API_KEY (optional — press enter to skip): ").strip()

    discord_webhook = existing.get("ASKR_DISCORD_WEBHOOK", "")
    if discord_webhook:
        console.print("  [dim]- ASKR_DISCORD_WEBHOOK already set[/dim]")
    else:
        # A webhook URL isn't a secret in the shoulder-surfing sense getpass()
        # protects against — and getpass() hides all input including paste, which
        # repeatedly looked like a hang to users pasting a long Discord URL here.
        discord_webhook = input("  ASKR_DISCORD_WEBHOOK (optional — press enter to skip): ").strip()

    if existing and anthropic_key == existing.get("ANTHROPIC_API_KEY", "") \
            and openai_key == existing.get("OPENAI_API_KEY", "") \
            and discord_webhook == existing.get("ASKR_DISCORD_WEBHOOK", ""):
        console.print("\n  [dim]nothing to change[/dim]\n")
        return

    os.makedirs(config_dir, exist_ok=True)
    with open(env_file, "w") as f:
        f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")
        if openai_key:
            f.write(f"OPENAI_API_KEY={openai_key}\n")
        if discord_webhook:
            f.write(f"ASKR_DISCORD_WEBHOOK={discord_webhook}\n")
        else:
            f.write(f"# ASKR_DISCORD_WEBHOOK=https://discord.com/api/webhooks/... (add to enable Discord alerts)\n")
    os.chmod(env_file, 0o600)  # contains plaintext API keys — default umask leaves this world-readable

    console.print("\n  [green]✓ saved[/green]  [dim]keys stored at[/dim] ~/.config/askr/.env\n")


def init_project():
    cwd = os.getcwd()

    skip = {"venv", "node_modules", ".git", "__pycache__", "dist", "build", ".llm_snapshot"}
    count = 0
    for _, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        count += sum(1 for f in files if os.path.splitext(f)[1] in {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
            ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h"
        })

    est_cost = count * 0.0012
    est_secs = count * 0.4  # concurrent  - roughly 6x faster than sequential
    print_init(cwd, count, est_cost, est_secs)
    build_snapshot(full=True, show_progress=True)

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

    console.print("\n  [dim]done  - run[/dim] [bold]ask \"your question\"[/bold] [dim]to start[/dim]\n")


def main():
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
        result, mode = _run_query(query)
        print_response(result, mode)


if __name__ == "__main__":
    main()
