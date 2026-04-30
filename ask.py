#!/usr/bin/env python3

import argparse
from main import run

parser = argparse.ArgumentParser()
parser.add_argument("query", type=str)
parser.add_argument("--mode", type=str)
parser.add_argument("--llm", type=str)

args = parser.parse_args()

print("\n" + run(args.query, args.mode, args.llm) + "\n")