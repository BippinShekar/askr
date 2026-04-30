#!/usr/bin/env python3

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run
from snapshot import build_snapshot
from logger import show_summary

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
        show_summary()
    else:
        query = " ".join(sys.argv[1:])
        print("\n" + run(query) + "\n")
