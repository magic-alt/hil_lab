#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time

from hil_pru_cli import HilPru, discover_device, hello
from hil_pru_protocol import (
    MSG_CAPTURE_CLEAR,
    MSG_CAPTURE_CONFIG,
    MSG_CAPTURE_START,
    MSG_CAPTURE_STATUS,
    MSG_CAPTURE_STOP,
    ns_to_ticks,
)
from hil_pwm_shared import read_consistent_snapshot, snapshot_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="hil_lab BBB PRU B1 PWM capture client")
    parser.add_argument("--device", help="RPMsg device; auto-detected by default")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    sub = parser.add_subparsers(dest="command", required=True)

    config = sub.add_parser("config")
    config.add_argument("--min-deadtime-ns", type=float, default=700.0)

    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("clear")
    sub.add_parser("status")

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--ring-limit", type=int, default=16)

    watch = sub.add_parser("watch")
    watch.add_argument("--interval-ms", type=float, default=100.0)
    watch.add_argument("--ring-limit", type=int, default=0)
    watch.add_argument("--count", type=int, default=0, help="0 means run until interrupted")

    args = parser.parse_args()

    if args.command in {"snapshot", "watch"}:
        if args.command == "snapshot":
            result = snapshot_to_dict(
                read_consistent_snapshot(),
                ring_limit=args.ring_limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        emitted = 0
        while args.count == 0 or emitted < args.count:
            result = snapshot_to_dict(
                read_consistent_snapshot(),
                ring_limit=args.ring_limit,
            )
            print(json.dumps(result, sort_keys=True), flush=True)
            emitted += 1
            time.sleep(args.interval_ms / 1000.0)
        return 0

    device = discover_device(args.device)
    client = HilPru(device, args.timeout_ms)
    try:
        info = hello(client)
        tick_hz = int(info["tick_hz"])

        if args.command == "config":
            min_ticks = ns_to_ticks(args.min_deadtime_ns, tick_hz)
            response = client.request(MSG_CAPTURE_CONFIG, arg0=min_ticks)
            result = {
                "status": response.flags,
                "min_deadtime_ticks": response.arg0,
                "min_deadtime_ns": response.arg0 * 1_000_000_000.0 / tick_hz,
            }
        elif args.command == "start":
            response = client.request(MSG_CAPTURE_START)
            result = {
                "status": response.flags,
                "start_ticks": response.arg0,
                "initial_input_bits": response.arg1,
            }
        elif args.command == "stop":
            response = client.request(MSG_CAPTURE_STOP)
            result = {"status": response.flags, "stop_ticks": response.arg0}
        elif args.command == "clear":
            response = client.request(MSG_CAPTURE_CLEAR)
            result = {"status": response.flags, "event_seq": response.arg0}
        else:
            response = client.request(MSG_CAPTURE_STATUS)
            result = {
                "status": response.flags,
                "running": bool(response.arg0),
                "min_deadtime_ticks": response.arg1,
                "min_deadtime_ns": response.arg1 * 1_000_000_000.0 / tick_hz,
                "fault_flags": response.arg2,
                "event_seq": response.arg3,
            }

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if int(result["status"]) == 0 else 2
    finally:
        client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
