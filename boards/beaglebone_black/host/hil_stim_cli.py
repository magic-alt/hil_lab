#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import sys

from hil_abz import (
    encode_config_flags,
    rpm_from_transition_ticks,
    transition_ticks_from_hz,
    transition_ticks_from_rpm,
)
from hil_pru_cli import HilPru, hello
from hil_pru_protocol import (
    MSG_ABZ_CONFIG,
    MSG_ABZ_DIRECTION,
    MSG_ABZ_START,
    MSG_ABZ_STATUS,
    MSG_ABZ_STOP,
    MSG_FORCE_SAFE,
)

ABZ_MIN_TRANSITION_TICKS = 100


def discover_stim_device(explicit: str | None) -> str:
    if explicit:
        return explicit

    candidates = ["/dev/rpmsg_pru31", "/dev/rpmsg-pru31"]
    candidates.extend(sorted(glob.glob("/dev/rpmsg*31*")))
    for candidate in candidates:
        try:
            with open(candidate, "rb", buffering=0):
                pass
        except OSError:
            continue
        return candidate

    raise FileNotFoundError(
        "PRU1 RPMsg device not found; expected /dev/rpmsg_pru31 "
        "or pass --device"
    )


def resolve_transition_ticks(args, tick_hz: int) -> tuple[int, float | None]:
    selected = sum(
        value is not None
        for value in (
            args.transition_ticks,
            args.transition_hz,
            args.rpm,
        )
    )
    if selected != 1:
        raise ValueError(
            "select exactly one of --transition-ticks, --transition-hz, or --rpm"
        )

    derived_rpm: float | None = None

    if args.transition_ticks is not None:
        ticks = args.transition_ticks
        if args.ppr:
            derived_rpm = rpm_from_transition_ticks(ticks, args.ppr, tick_hz)
    elif args.transition_hz is not None:
        ticks = transition_ticks_from_hz(args.transition_hz, tick_hz)
        if args.ppr:
            derived_rpm = rpm_from_transition_ticks(ticks, args.ppr, tick_hz)
    else:
        if not args.ppr:
            raise ValueError("--rpm requires --ppr")
        ticks = transition_ticks_from_rpm(args.rpm, args.ppr, tick_hz)
        derived_rpm = args.rpm

    if ticks < ABZ_MIN_TRANSITION_TICKS:
        raise ValueError(
            f"requested rate requires {ticks} PRU ticks/transition; "
            f"current unqualified floor is {ABZ_MIN_TRANSITION_TICKS}"
        )

    return ticks, derived_rpm


def main() -> int:
    parser = argparse.ArgumentParser(
        description="hil_lab BBB PRU1 B2 ABZ stimulus client"
    )
    parser.add_argument("--device", help="PRU1 RPMsg device; defaults to port 31")
    parser.add_argument("--timeout-ms", type=int, default=1000)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hello")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("safe")

    config = sub.add_parser("config")
    config.add_argument("--transition-ticks", type=int)
    config.add_argument("--transition-hz", type=float)
    config.add_argument("--rpm", type=float)
    config.add_argument("--ppr", type=int)
    config.add_argument(
        "--direction",
        choices=("forward", "reverse"),
        default="forward",
    )
    config.add_argument("--initial-phase", type=int, default=0)
    config.add_argument("--index-period-transitions", type=int)
    config.add_argument("--index-width-transitions", type=int, default=1)

    direction = sub.add_parser("direction")
    direction.add_argument("value", choices=("forward", "reverse"))

    args = parser.parse_args()
    device = discover_stim_device(args.device)
    client = HilPru(device, args.timeout_ms)

    try:
        if args.command == "hello":
            result = hello(client)

        elif args.command == "config":
            info = hello(client)
            tick_hz = int(info["tick_hz"])
            ticks, derived_rpm = resolve_transition_ticks(args, tick_hz)

            if args.index_period_transitions is None:
                index_period = args.ppr * 4 if args.ppr else 0
            else:
                index_period = args.index_period_transitions

            index_width = args.index_width_transitions if index_period else 0
            if index_period < 0 or index_width < 0:
                raise ValueError("index transition counts must be non-negative")
            if index_period and index_width > index_period:
                raise ValueError("index width cannot exceed index period")

            flags = encode_config_flags(args.direction, args.initial_phase)

            response = client.request(
                MSG_ABZ_CONFIG,
                arg0=ticks,
                arg1=index_period,
                arg2=index_width,
                arg3=flags,
            )

            transition_hz = tick_hz / ticks
            result = {
                "status": response.flags,
                "tick_hz": tick_hz,
                "transition_ticks": response.arg0,
                "transition_hz": transition_hz,
                "ppr": args.ppr,
                "equivalent_rpm": derived_rpm,
                "direction": args.direction,
                "initial_phase": args.initial_phase,
                "index_period_transitions": response.arg1,
                "index_width_transitions": response.arg2,
            }

        elif args.command == "start":
            response = client.request(MSG_ABZ_START)
            result = {
                "status": response.flags,
                "actual_start_ticks": response.arg0,
                "initial_abz_bits": response.arg1,
                "first_transition_ticks": response.arg2,
                "direction": "reverse" if response.arg3 else "forward",
            }

        elif args.command == "stop":
            response = client.request(MSG_ABZ_STOP)
            result = {
                "status": response.flags,
                "actual_stop_ticks": response.arg0,
                "transition_count": response.arg1,
                "late_transition_count": response.arg2,
            }

        elif args.command == "status":
            response = client.request(MSG_ABZ_STATUS)
            result = {
                "status": response.flags,
                "running": bool(response.arg0),
                "transition_ticks": response.arg1,
                "transition_count": response.arg2,
                "late_transition_count": response.arg3,
            }

        elif args.command == "direction":
            requested = 0 if args.value == "forward" else 1
            response = client.request(MSG_ABZ_DIRECTION, arg0=requested)
            result = {
                "status": response.flags,
                "actual_apply_ticks": response.arg0,
                "direction": "reverse" if response.arg1 else "forward",
                "transition_count": response.arg2,
            }

        else:
            response = client.request(MSG_FORCE_SAFE)
            result = {
                "status": response.flags,
                "actual_safe_ticks": response.arg0,
                "transition_count": response.arg1,
            }

        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if int(result.get("status", 0)) == 0 else 2
    finally:
        client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
