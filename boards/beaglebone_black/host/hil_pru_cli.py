#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import select
import statistics
import sys
import time
from pathlib import Path
from typing import Iterable

from hil_pru_protocol import (
    CAP_FORCE_SAFE,
    CAP_GPIO_LOOPBACK,
    CAP_RPMSG,
    CAP_SHARED_SNAPSHOT,
    CAP_TIMEBASE,
    CAP_WATCHDOG,
    CAP_PWM_CAPTURE,
    CAP_PWM_COMPLEMENTARY_MONITOR,
    CAP_RAW_EDGE_CAPTURE,
    CAP_STIMULUS_ENGINE,
    CAP_ABZ_EMULATOR,
    CAP_SCHEDULED_GPIO,
    CAP_HALL_EMULATOR,
    CAP_SSI_EMULATOR,
    CAP_BISS_EMULATOR,
    CAP_SPI_SENSOR_EMULATOR,
    CAP_SCHEDULED_APPLY,
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
    CAP_PWM_CAPTURE: "pwm_capture",
    CAP_PWM_COMPLEMENTARY_MONITOR: "pwm_complementary_monitor",
    CAP_SHARED_SNAPSHOT: "shared_snapshot",
    CAP_RAW_EDGE_CAPTURE: "raw_edge_capture",
    CAP_STIMULUS_ENGINE: "stimulus_engine",
    CAP_ABZ_EMULATOR: "abz_emulator",
    CAP_SCHEDULED_GPIO: "scheduled_gpio",
    CAP_HALL_EMULATOR: "hall_emulator",
    CAP_SSI_EMULATOR: "ssi_emulator",
    CAP_BISS_EMULATOR: "biss_emulator",
    CAP_SPI_SENSOR_EMULATOR: "spi_sensor_emulator",
    CAP_SCHEDULED_APPLY: "scheduled_apply",
}


class HilPru:
    """Persistent host connection to one PRU RPMsg character device."""

    def __init__(self, device: str, timeout_ms: int = 1000) -> None:
        self.device = device
        self.timeout_ms = timeout_ms
        self.fd = os.open(device, os.O_RDWR | os.O_CLOEXEC)
        self.seq = 1
        self.poller = select.poll()
        self.poller.register(self.fd, select.POLLIN | select.POLLERR | select.POLLHUP)

    def close(self) -> None:
        try:
            self.poller.unregister(self.fd)
        except KeyError:
            pass
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

        events = self.poller.poll(self.timeout_ms)
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


def percentile(values: Iterable[float], p: float) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        raise ValueError("percentile requires at least one sample")
    if not 0.0 <= p <= 100.0:
        raise ValueError("percentile must be in [0, 100]")
    if len(ordered) == 1:
        return ordered[0]

    rank = (len(ordered) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return ordered[low] + ((ordered[high] - ordered[low]) * fraction)


def summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 50.0),
        "p95": percentile(values, 95.0),
        "p99": percentile(values, 99.0),
        "max": max(values),
        "stdev": statistics.pstdev(values),
    }


def loopback_once(
    client: HilPru,
    tick_hz: int,
    *,
    delay_us: float,
    width_us: float,
    timeout_us: float,
) -> dict[str, float | int | None]:
    host_start_ns = time.perf_counter_ns()
    response = client.request(
        MSG_GPIO_LOOPBACK,
        arg0=us_to_ticks(delay_us, tick_hz),
        arg1=us_to_ticks(width_us, tick_hz),
        arg2=us_to_ticks(timeout_us, tick_hz),
    )
    host_end_ns = time.perf_counter_ns()

    rise_latency_ticks = (
        None
        if response.arg1 == 0xFFFFFFFF
        else ((response.arg1 - response.arg0) & 0xFFFFFFFF)
    )
    high_ticks = None
    if response.arg1 != 0xFFFFFFFF and response.arg2 != 0xFFFFFFFF:
        high_ticks = (response.arg2 - response.arg1) & 0xFFFFFFFF

    command_rtt_us = (host_end_ns - host_start_ns) / 1000.0
    programmed_us = delay_us + width_us

    return {
        "status": response.flags,
        "requested_start_ticks": response.arg0,
        "observed_rise_ticks": response.arg1,
        "observed_fall_ticks": response.arg2,
        "response_ticks": response.arg3,
        "rise_latency_us": (
            None if rise_latency_ticks is None else ticks_to_us(rise_latency_ticks, tick_hz)
        ),
        "observed_high_us": (
            None if high_ticks is None else ticks_to_us(high_ticks, tick_hz)
        ),
        "command_rtt_us": command_rtt_us,
        "non_programmed_rtt_us": command_rtt_us - programmed_us,
        "tick_hz": tick_hz,
    }


def run_loopback_benchmark(
    client: HilPru,
    *,
    count: int,
    warmup: int,
    delay_us: float,
    width_us: float,
    timeout_us: float,
) -> dict[str, object]:
    if count <= 0:
        raise ValueError("--count must be > 0")
    if warmup < 0:
        raise ValueError("--warmup must be >= 0")

    info = hello(client)
    if int(info["status"]) != 0:
        raise RuntimeError(f"HELLO failed with status={info['status']}")
    tick_hz = int(info["tick_hz"])

    for _ in range(warmup):
        sample = loopback_once(
            client,
            tick_hz,
            delay_us=delay_us,
            width_us=width_us,
            timeout_us=timeout_us,
        )
        if int(sample["status"]) != 0:
            raise RuntimeError(f"warmup loopback failed with status={sample['status']}")

    rise: list[float] = []
    high: list[float] = []
    high_error: list[float] = []
    rtt: list[float] = []
    non_programmed_rtt: list[float] = []
    failures: list[dict[str, object]] = []

    total_start_ns = time.perf_counter_ns()
    for index in range(count):
        try:
            sample = loopback_once(
                client,
                tick_hz,
                delay_us=delay_us,
                width_us=width_us,
                timeout_us=timeout_us,
            )
        except Exception as exc:
            failures.append({"index": index, "error": str(exc)})
            continue

        if int(sample["status"]) != 0:
            failures.append({"index": index, "status": int(sample["status"])})
            continue

        rise_value = sample["rise_latency_us"]
        high_value = sample["observed_high_us"]
        if rise_value is None or high_value is None:
            failures.append({"index": index, "error": "missing PRU edge timestamp"})
            continue

        rise.append(float(rise_value))
        high.append(float(high_value))
        high_error.append(float(high_value) - width_us)
        rtt.append(float(sample["command_rtt_us"]))
        non_programmed_rtt.append(float(sample["non_programmed_rtt_us"]))

    total_elapsed_s = (time.perf_counter_ns() - total_start_ns) / 1_000_000_000.0
    attempted_hz = count / total_elapsed_s if total_elapsed_s > 0 else 0.0
    success_hz = len(rise) / total_elapsed_s if total_elapsed_s > 0 else 0.0

    return {
        "device": client.device,
        "count_requested": count,
        "samples_ok": len(rise),
        "failures": len(failures),
        "failure_rate": len(failures) / count,
        "failure_examples": failures[:10],
        "warmup": warmup,
        "delay_us": delay_us,
        "width_us": width_us,
        "programmed_cycle_us": delay_us + width_us,
        "timeout_us": timeout_us,
        "total_elapsed_s": total_elapsed_s,
        "attempt_rate_hz": attempted_hz,
        "success_rate_hz": success_hz,
        "tick_hz": tick_hz,
        "rise_latency_us": summarize(rise),
        "observed_high_us": summarize(high),
        "high_width_error_us": summarize(high_error),
        "command_rtt_us": summarize(rtt),
        "non_programmed_rtt_us": summarize(non_programmed_rtt),
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

    loop = sub.add_parser("loopback", help="schedule P9_31 pulse and measure jumper on P9_29")
    loop.add_argument("--delay-us", type=float, default=1000.0)
    loop.add_argument("--width-us", type=float, default=1000.0)
    loop.add_argument("--timeout-us", type=float, default=5000.0)

    bench = sub.add_parser(
        "bench-loopback",
        help="benchmark loopback with one persistent Python/RPMsg session",
    )
    bench.add_argument("--count", type=int, default=1000)
    bench.add_argument("--warmup", type=int, default=10)
    bench.add_argument("--delay-us", type=float, default=1000.0)
    bench.add_argument("--width-us", type=float, default=1000.0)
    bench.add_argument("--timeout-us", type=float, default=5000.0)

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
        elif args.command == "loopback":
            info = hello(client)
            tick_hz = int(info["tick_hz"])
            result = loopback_once(
                client,
                tick_hz,
                delay_us=args.delay_us,
                width_us=args.width_us,
                timeout_us=args.timeout_us,
            )
        else:
            result = run_loopback_benchmark(
                client,
                count=args.count,
                warmup=args.warmup,
                delay_us=args.delay_us,
                width_us=args.width_us,
                timeout_us=args.timeout_us,
            )

        print(json.dumps(result, indent=2, sort_keys=True))
        if args.command == "bench-loopback":
            return 0 if int(result.get("failures", 1)) == 0 else 2
        return 0 if int(result.get("status", 0)) == 0 else 2
    finally:
        client.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
