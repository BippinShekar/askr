#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run
from snapshot import build_snapshot

def show_log():
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".askr_log")
    if not os.path.exists(log_path):
        print("No usage logged yet.")
        return
    with open(log_path) as f:
        lines = f.readlines()
    print(f"\n{'─'*40}")
    print(f"  askr — last {min(20, len(lines))} queries")
    print(f"{'─'*40}")
    for line in lines[-20:]:
        print(line.rstrip())
    print(f"{'─'*40}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ask \"cto: your question\"")
        print("       ask snap")
        print("       ask log")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "snap":
        print("Building snapshot...")
        build_snapshot()
        print("Done.")
    elif cmd == "log":
        show_log()
    else:
        query = " ".join(sys.argv[1:])
        print("\n" + run(query) + "\n")
