#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from hil_pru_cli import HilPru, hello
from hil_pru_protocol import (
    MSG_FORCE_SAFE,
    MSG_SERIAL_CONFIG,
    MSG_SERIAL_DATA,
    MSG_SERIAL_START,
    MSG_SERIAL_STATUS,
    MSG_SERIAL_STOP,
    us_to_ticks,
)
from hil_sensor import (
    SERIAL_FLAG_BISS_ERROR_OK,
    SERIAL_FLAG_BISS_WARNING_OK,
    SERIAL_FLAG_FAULT_ENABLE,
    SERIAL_MODE_BISS,
    SERIAL_MODE_SPI,
    SERIAL_MODE_SSI,
    build_biss_frame,
    mode_name,
)
from hil_stim_cli import discover_stim_device


MODE_BY_NAME = {
    "ssi": SERIAL_MODE_SSI,
    "biss": SERIAL_MODE_BISS,
    "spi": SERIAL_MODE_SPI,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="hil_lab BBB PRU1 B2 serial encoder/sensor emulator client"
    )
    parser.add_argument("--device", help="PRU1 RPMsg device; defaults to port 31")
    parser.add_argument("--timeout-ms", type=int, default=1000)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hello")

    config = sub.add_parser("config")
    config.add_argument("--mode", choices=tuple(MODE_BY_NAME), required=True)
    config.add_argument("--bits", type=int, required=True)
    config.add_argument("--gap-us", type=float, default=1.0)

    data = sub.add_parser("data")
    data.add_argument("--value", type=lambda value: int(value, 0), required=True)
    data.add_argument("--fault-mask", type=lambda value: int(value, 0), default=0)
    data.add_argument("--fault-enable", action="store_true")
    data.add_argument("--error-active", action="store_true")
    data.add_argument("--warning-active", action="store_true")
    data.add_argument(
        "--preview-biss-bits",
        type=int,
        help="print the expected BiSS frame for this position bit width",
    )

    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("safe")

    args = parser.parse_args()
    device = discover_stim_device(args.device)
    client = HilPru(device, args.timeout_ms)

    try:
        if args.command == "hello":
            result = hello(client)

        elif args.command == "config":
            info = hello(client)
            tick_hz = int(info["tick_hz"])
            if not 1 <= args.bits <= 32:
                raise ValueError("--bits must be 1..32")
            if args.gap_us < 0:
                raise ValueError("--gap-us must be >= 0")
            gap_ticks = us_to_ticks(args.gap_us, tick_hz)
            mode = MODE_BY_NAME[args.mode]
            response = client.request(
                MSG_SERIAL_CONFIG,
                arg0=mode,
                arg1=args.bits,
                arg2=gap_ticks,
                arg3=0,
            )
            result = {
                "status": response.flags,
                "mode": mode_name(response.arg0),
                "bits": response.arg1,
                "frame_gap_ticks": response.arg2,
                "frame_gap_us": (
                    response.arg2 * 1_000_000.0 / tick_hz
                    if tick_hz else None
                ),
            }

        elif args.command == "data":
            flags = 0
            if args.fault_enable:
                flags |= SERIAL_FLAG_FAULT_ENABLE
            if not args.error_active:
                flags |= SERIAL_FLAG_BISS_ERROR_OK
            if not args.warning_active:
                flags |= SERIAL_FLAG_BISS_WARNING_OK

            response = client.request(
                MSG_SERIAL_DATA,
                arg0=args.value & 0xFFFFFFFF,
                arg1=args.fault_mask & 0xFFFFFFFF,
                arg2=flags,
            )
            result = {
                "status": response.flags,
                "value": f"0x{response.arg0:08x}",
                "fault_mask": f"0x{response.arg1:08x}",
                "flags": response.arg2,
            }
            if args.preview_biss_bits is not None:
                frame, total_bits = build_biss_frame(
                    args.value,
                    args.preview_biss_bits,
                    error_ok=0 if args.error_active else 1,
                    warning_ok=0 if args.warning_active else 1,
                )
                result["biss_preview"] = {
                    "total_bits": total_bits,
                    "frame_hex": hex(frame),
                    "frame_binary": format(frame, f"0{total_bits}b"),
                }

        elif args.command == "start":
            response = client.request(MSG_SERIAL_START)
            result = {
                "status": response.flags,
                "arm_request_ticks": response.arg0,
                "mode": mode_name(response.arg1),
                "bits": response.arg2,
                "semantics": "ACK sent before serial edge baselines are armed",
            }

        elif args.command == "stop":
            response = client.request(MSG_SERIAL_STOP)
            result = {
                "status": response.flags,
                "actual_stop_ticks": response.arg0,
                "frame_count": response.arg1,
                "min_half_period_ticks": response.arg2,
                "protocol_error_count": response.arg3,
            }

        elif args.command == "status":
            info = hello(client)
            tick_hz = int(info["tick_hz"])
            response = client.request(MSG_SERIAL_STATUS)
            enabled = bool(response.arg0 & 1)
            mode = (response.arg0 >> 8) & 0xFF
            min_half = response.arg2
            result = {
                "status": response.flags,
                "enabled": enabled,
                "mode": mode_name(mode),
                "frame_count": response.arg1,
                "min_half_period_ticks": min_half,
                "measured_clock_ceiling_hz": (
                    tick_hz / (2.0 * min_half) if min_half else None
                ),
                "protocol_error_count": response.arg3,
            }

        else:
            response = client.request(MSG_FORCE_SAFE)
            result = {
                "status": response.flags,
                "actual_safe_ticks": response.arg0,
                "frame_count": response.arg1,
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
