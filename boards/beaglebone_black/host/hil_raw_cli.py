#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time

from hil_pru_cli import HilPru, discover_device, hello
from hil_pru_protocol import (
    MSG_RAW_CLEAR,
    MSG_RAW_CONFIG,
    MSG_RAW_START,
    MSG_RAW_STATUS,
    MSG_RAW_STOP,
)
from hil_raw_shared import (
    RAW_CAPACITY,
    analyze_raw_capture,
    raw_records,
    read_frozen_raw_capture,
)


def status_dict(response) -> dict[str, object]:
    return {
        "status": response.flags,
        "running": bool(response.arg0),
        "event_count": response.arg1,
        "event_limit": response.arg2,
        "stop_reason": response.arg3,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="hil_lab BBB PRU0 B1 raw-edge capture client"
    )
    parser.add_argument("--device", help="RPMsg device; auto-detected by default")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hello")

    config = sub.add_parser("config")
    config.add_argument(
        "--event-limit",
        type=int,
        default=RAW_CAPACITY,
        help=f"bounded precise-capture event count (1..{RAW_CAPACITY})",
    )

    sub.add_parser("clear")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")

    dump = sub.add_parser("dump")
    dump.add_argument("--limit", type=int, default=32)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("--min-deadtime-ns", type=float, default=0.0)

    capture = sub.add_parser(
        "capture",
        help="configure/start bounded capture, wait without RPMsg, then analyze",
    )
    capture.add_argument("--event-limit", type=int, default=RAW_CAPACITY)
    capture.add_argument(
        "--settle-ms",
        type=float,
        default=100.0,
        help="host sleep before first post-capture status query",
    )
    capture.add_argument("--min-deadtime-ns", type=float, default=0.0)

    args = parser.parse_args()

    if args.command in {"dump", "analyze"}:
        shared = read_frozen_raw_capture()

        if args.command == "dump":
            records = raw_records(shared)
            limit = max(0, min(args.limit, len(records)))
            result = {
                "running": bool(shared.running),
                "event_count": int(shared.event_count),
                "event_limit": int(shared.configured_event_limit),
                "stop_reason": int(shared.stop_reason),
                "tick_hz": int(shared.tick_hz),
                "records": records[-limit:] if limit else [],
            }
        else:
            result = analyze_raw_capture(
                shared,
                min_deadtime_ns=args.min_deadtime_ns,
            )

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    device = discover_device(args.device)
    client = HilPru(device, args.timeout_ms)
    try:
        if args.command == "hello":
            result = hello(client)

        elif args.command == "config":
            if not 1 <= args.event_limit <= RAW_CAPACITY:
                raise ValueError(f"--event-limit must be 1..{RAW_CAPACITY}")
            response = client.request(MSG_RAW_CONFIG, arg0=args.event_limit)
            result = {
                "status": response.flags,
                "event_limit": response.arg0,
                "capacity": response.arg1,
            }

        elif args.command == "clear":
            response = client.request(MSG_RAW_CLEAR)
            result = {
                "status": response.flags,
                "generation": response.arg0,
            }

        elif args.command == "start":
            response = client.request(MSG_RAW_START)
            result = {
                "status": response.flags,
                "arm_request_ticks": response.arg0,
                "prearm_raw_inputs": response.arg1,
                "event_limit": response.arg2,
            }

        elif args.command == "stop":
            response = client.request(MSG_RAW_STOP)
            result = {
                "status": response.flags,
                "stop_ticks": response.arg0,
                "event_count": response.arg1,
                "stop_reason": response.arg2,
            }

        elif args.command == "status":
            result = status_dict(client.request(MSG_RAW_STATUS))

        else:
            if not 1 <= args.event_limit <= RAW_CAPACITY:
                raise ValueError(f"--event-limit must be 1..{RAW_CAPACITY}")
            if args.settle_ms < 0:
                raise ValueError("--settle-ms must be >= 0")

            cfg = client.request(MSG_RAW_CONFIG, arg0=args.event_limit)
            if cfg.flags:
                raise RuntimeError(f"RAW_CONFIG failed: status={cfg.flags}")

            cleared = client.request(MSG_RAW_CLEAR)
            if cleared.flags:
                raise RuntimeError(f"RAW_CLEAR failed: status={cleared.flags}")

            started = client.request(MSG_RAW_START)
            if started.flags:
                raise RuntimeError(f"RAW_START failed: status={started.flags}")

            # Critical design rule: no RPMsg traffic during the precise window.
            time.sleep(args.settle_ms / 1000.0)

            status = client.request(MSG_RAW_STATUS)
            state = status_dict(status)
            if status.flags:
                raise RuntimeError(f"RAW_STATUS failed: status={status.flags}")
            if state["running"]:
                raise RuntimeError(
                    "capture still running after settle interval; do not poll it "
                    "repeatedly because RPMsg perturbs precise capture. Increase "
                    "--settle-ms or lower --event-limit/input rate."
                )

            shared = read_frozen_raw_capture()
            result = {
                "control": {
                    "arm_request_ticks": started.arg0,
                    "prearm_raw_inputs": started.arg1,
                    **state,
                },
                "analysis": analyze_raw_capture(
                    shared,
                    min_deadtime_ns=args.min_deadtime_ns,
                ),
            }

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if int(result.get("status", 0)) == 0 else 2
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
