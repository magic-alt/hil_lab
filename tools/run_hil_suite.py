#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser=argparse.ArgumentParser(description="run hardware-required hil_lab pytest suite")
    parser.add_argument("resource_json")
    parser.add_argument("--junitxml",default="build/hil-junit.xml")
    args=parser.parse_args()
    cmd=[
        sys.executable,"-m","pytest","tests/hil","-m","hil",
        "--hil-resource",args.resource_json,
        "--junitxml",args.junitxml,
    ]
    return subprocess.call(cmd)

if __name__=="__main__":
    raise SystemExit(main())
