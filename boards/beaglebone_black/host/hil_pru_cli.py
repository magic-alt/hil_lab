#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import select
import sys
from pathlib import Path

from hil_pru_protocol import (
    CAP_FORCE_SAFE,
    CAP_GPIO_LOOPBACK,
    CAP_RPMSG,
    CAP_TIMEBASE,
    CAP_WATCHDOG,
    MSG_FORCE_SAFE,
    MSG_GPIO_LOOPBACK,
    MSG_HELLO,
    MSG_PING,
    MSG_TIME,
    Message,
    ticks_to_us,
    us_to_ticks,
)

CAP_NAMES = {
    CAP_TIMEBASE: "timebase",
    CAP_RPMSG: "rpmsg",
    CAP_GPIO_LOOPBACK: "gpio_loopback",
    CAP_FORCE_SAFE: "force_safe",
    CAP_WATCHDOG: "watchdog",
}


class HilPru:
    def __init__(self, device: str, timeout_ms: int = 1000) -> None:
        self.device = device
        self.timeout_ms = timeout_ms
        self.fd = os.open(device, os.O_RDWR | os.O_CLOEXEC)
        self.seq = 1

    def close(self) -> None:
        os.close(self.fd)

    def request(
        self,
        msg_type: int,
        *,
        arg0: int = 0,
        arg1: int = 0,
        arg2: int = 0,
        arg3: int = 0,
    ) -> Message:
        seq = self.seq
        self.seq += 1
        request = Message(
            type=msg_type,
            seq=seq,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
        )
        packet = request.pack()
        written = os.write(self.fd, packet)
        if written != len(packet):
            raise RuntimeError(f"short RPMsg write: {written}/{len(packet)}")

        poller = select.poll()
        poller.register(self.fd, select.POLLIN | select.POLLERR | select.POLLHUP)
        events = poller.poll(self.timeout_ms)
        if not events:
            raise TimeoutError(f"RPMsg response timeout after {self.timeout_ms} ms")
        if events[0][1] & (select.POLLERR | select.POLLHUP):
            raise RuntimeError(f"RPMsg device error: event mask=0x{events[0][1]:x}")

        payload = os.read(self.fd, 512)
        response = Message.unpack(payload)
        response.validate_response(msg_type, seq)
        return response


def discover_device(explicit: str | None) -> str:
    if explicit:
        return explicit
    candidates = ["/dev/rpmsg_pru30", "/dev/rpmsg-pru30"]
    candidates.extend(sorted(glob.glob("/dev/rpmsg*30*")))
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("PRU0 RPMsg device not found; start firmware or pass --device")


def hello(client: HilPru) -> dict[str, object]:
    response = client.request(MSG_HELLO)
    caps = response.arg0
    return {
        "status": response.flags,
        "capabilities_raw": caps,
        "capabilities": [name for bit, name in CAP_NAMES.items() if caps & bit],
        "tick_hz": response.arg1,
        "counter_bits": response.arg2,
        "firmware_version": f"0x{response.arg3:08x}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="hil_lab BBB PRU B0 RPMsg client")
    parser.add_argument("--device", help="RPMsg character device; auto-detected by default")
    parser.add_argument("--timeout-ms", type=int, default=1000)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("hello")
    sub.add_parser("time")
    sub.add_parser("ping")
    sub.add_parser("safe")

    loop = sub.add_parser("loopback", help="schedule P9_31 pulse and measure jumper on P9_25")
    loop.add_argument("--delay-us", type=float, default=1000.0)
    loop.add_argument("--width-us", type=float, default=1000.0)
    loop.add_argument("--timeout-us", type=float, default=5000.0)

    args = parser.parse_args()
    device = discover_device(args.device)
    client = HilPru(device, args.timeout_ms)
    try:
        if args.command == "hello":
            result = hello(client)
        elif args.command == "time":
            response = client.request(MSG_TIME)
            result = {
                "status": response.flags,
                "ticks": response.arg0,
                "tick_hz": response.arg1,
                "counter_bits": response.arg2,
            }
        elif args.command == "ping":
            response = client.request(MSG_PING)
            result = {"status": response.flags, "ticks": response.arg0}
        elif args.command == "safe":
            response = client.request(MSG_FORCE_SAFE)
            result = {"status": response.flags, "ticks": response.arg0}
        else:
            info = hello(client)
            tick_hz = int(info["tick_hz"])
            response = client.request(
                MSG_GPIO_LOOPBACK,
                arg0=us_to_ticks(args.delay_us, tick_hz),
                arg1=us_to_ticks(args.width_us, tick_hz),
                arg2=us_to_ticks(args.timeout_us, tick_hz),
            )
            rise_latency = (
                None
                if response.arg1 == 0xFFFFFFFF
                else ((response.arg1 - response.arg0) & 0xFFFFFFFF)
            )
            fall_from_rise = None
            if response.arg1 != 0xFFFFFFFF and response.arg2 != 0xFFFFFFFF:
                fall_from_rise = (response.arg2 - response.arg1) & 0xFFFFFFFF
            result = {
                "status": response.flags,
                "requested_start_ticks": response.arg0,
                "observed_rise_ticks": response.arg1,
                "observed_fall_ticks": response.arg2,
                "response_ticks": response.arg3,
                "rise_latency_us": (
                    None if rise_latency is None else ticks_to_us(rise_latency, tick_hz)
                ),
                "observed_high_us": (
                    None
                    if fall_from_rise is None
                    else ticks_to_us(fall_from_rise, tick_hz)
                ),
                "tick_hz": tick_hz,
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
