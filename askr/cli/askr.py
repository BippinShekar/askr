#!/usr/bin/env python3

import sys
from askr.utils.display import console


def main():
    if len(sys.argv) < 2:
        console.print("\n  [bold]askr[/bold]  [dim]session orchestration for Claude Code[/dim]")
        console.print()
        console.print("  [dim]askr init       - set up session orchestration in this project[/dim]")
        console.print("  [dim]askr launch     - start Claude Code under Askr management[/dim]")
        console.print("  [dim]askr status     - show current session state[/dim]")
        console.print("  [dim]askr log        - show session history and time saved[/dim]")
        console.print()
        console.print("  [dim]session orchestration coming in Phase 1[/dim]\n")
        sys.exit(0)

    cmd = sys.argv[1]
    console.print(f"\n  [yellow]⚠ askr {cmd}  - session orchestration not yet implemented[/yellow]")
    console.print("  [dim]see roadmap.md for the build timeline[/dim]\n")


if __name__ == "__main__":
    main()
