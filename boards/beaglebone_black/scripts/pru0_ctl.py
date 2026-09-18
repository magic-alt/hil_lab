#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys
import time
from pathlib import Path

DEFAULT_FIRMWARE_NAME = "hil-b0-pru0-fw"
PRU0_NAMES = ("4a334000.pru", "4a334000.pru0", "pruss-core0")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def find_pru0_remoteproc(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    matches: list[Path] = []
    for raw in sorted(glob.glob("/sys/class/remoteproc/remoteproc*")):
        path = Path(raw)
        try:
            name = read_text(path / "name")
        except OSError:
            continue
        lower = name.lower()
        if name in PRU0_NAMES or "4a334000.pru" in lower or "pruss-core0" in lower:
            matches.append(path)
    if len(matches) != 1:
        found = []
        for raw in sorted(glob.glob("/sys/class/remoteproc/remoteproc*")):
            path = Path(raw)
            try:
                found.append(f"{path.name}:{read_text(path / 'name')}")
            except OSError:
                pass
        raise RuntimeError(f"could not uniquely identify PRU0 remoteproc; found {found}")
    return matches[0]


def write_control(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")


def state(remoteproc: Path) -> str:
    return read_text(remoteproc / "state")


def stop(remoteproc: Path) -> None:
    if state(remoteproc) == "running":
        write_control(remoteproc / "state", "stop")


def start(remoteproc: Path) -> None:
    if state(remoteproc) != "running":
        write_control(remoteproc / "state", "start")


def install_and_start(remoteproc: Path, source: Path, firmware_name: str) -> None:
    if os.geteuid() != 0:
        raise PermissionError("deploy requires root; run with sudo")
    if not source.is_file():
        raise FileNotFoundError(source)

    stop(remoteproc)
    destination = Path("/lib/firmware") / firmware_name
    shutil.copy2(source, destination)
    write_control(remoteproc / "firmware", firmware_name)
    start(remoteproc)


def wait_for_rpmsg(timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    patterns = ("/dev/rpmsg_pru30", "/dev/rpmsg-pru30", "/dev/rpmsg*30*")
    while time.monotonic() < deadline:
        for pattern in patterns:
            for candidate in glob.glob(pattern):
                if Path(candidate).exists():
                    return candidate
        time.sleep(0.05)
    raise TimeoutError("RPMsg PRU0 character device did not appear")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage BBB PRU0 remoteproc for hil_lab B0")
    parser.add_argument("--remoteproc", help="override /sys/class/remoteproc/remoteprocN")
    parser.add_argument("--firmware-name", default=DEFAULT_FIRMWARE_NAME)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("start")
    sub.add_parser("stop")
    deploy = sub.add_parser("deploy")
    deploy.add_argument("firmware", type=Path)
    deploy.add_argument("--wait-rpmsg", type=float, default=2.0)

    args = parser.parse_args()
    remoteproc = find_pru0_remoteproc(args.remoteproc)

    if args.command == "status":
        print(f"remoteproc={remoteproc}")
        print(f"name={read_text(remoteproc / 'name')}")
        print(f"state={state(remoteproc)}")
        print(f"firmware={read_text(remoteproc / 'firmware')}")
    elif args.command == "start":
        start(remoteproc)
        print(state(remoteproc))
    elif args.command == "stop":
        stop(remoteproc)
        print(state(remoteproc))
    else:
        install_and_start(remoteproc, args.firmware, args.firmware_name)
        device = wait_for_rpmsg(args.wait_rpmsg)
        print(f"remoteproc={remoteproc}")
        print(f"rpmsg={device}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
