#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run
from snapshot import build_snapshot
from logger import show_summary


def init_project():
    cwd = os.getcwd()

    # Count files that will be summarized
    skip = {"venv", "node_modules", ".git", "__pycache__", "dist", "build", ".llm_snapshot"}
    count = 0
    for _, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        count += sum(1 for f in files if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")))

    est_cost = count * 0.0012
    print(f"\n  askr init — {cwd}")
    print(f"  {count} file(s) to index, estimated cost: ~${est_cost:.3f}")
    print("  building snapshot...\n")

    build_snapshot(full=True)

    # Add askr artifacts to project's .gitignore if one exists
    gitignore = os.path.join(cwd, ".gitignore")
    entries = [".llm_snapshot/", ".askr_history"]
    if os.path.exists(gitignore):
        existing = open(gitignore).read()
        additions = [e for e in entries if e not in existing]
        if additions:
            with open(gitignore, "a") as f:
                f.write("\n# askr\n" + "\n".join(additions) + "\n")
            print(f"  added to .gitignore: {', '.join(additions)}")

    print("\n  done. run 'ask \"your question\"' to start.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ask \"cto: your question\"")
        print("       ask init")
        print("       ask snap")
        print("       ask log")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        init_project()
    elif cmd == "snap":
        print("Rebuilding snapshot...")
        build_snapshot(full=True)
        print("Done.")
    elif cmd == "log":
        show_summary()
    else:
        query = " ".join(sys.argv[1:])
        print("\n" + run(query) + "\n")
