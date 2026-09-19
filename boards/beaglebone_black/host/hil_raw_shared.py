from __future__ import annotations

import ctypes
import mmap
import os
import statistics
from collections import Counter
from dataclasses import dataclass

PRUSS_SHARED_PHYS_BASE = 0x4A310000
PRUSS_SHARED_SIZE = 0x3000

RAW_MAGIC = 0x31574152
RAW_VERSION = 1
RAW_CAPACITY = 1024

RAW_STOP_NONE = 0
RAW_STOP_EVENT_LIMIT = 1
RAW_STOP_HOST_REQUEST = 2
RAW_STOP_FORCE_SAFE = 3

CHANNEL_NAMES = ("UH", "UL", "VH", "VL", "WH", "WL")
PAIR_NAMES = ("U", "V", "W")
RAW_MASKS = (1 << 1, 1 << 2, 1 << 3, 1 << 5, 1 << 14, 1 << 15)


class RawEdgeRecord(ctypes.LittleEndianStructure):
    _fields_ = [
        ("timestamp_ticks", ctypes.c_uint32),
        ("raw_inputs", ctypes.c_uint32),
    ]


class RawCaptureShared(ctypes.LittleEndianStructure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("total_size", ctypes.c_uint32),
        ("tick_hz", ctypes.c_uint32),

        ("capacity", ctypes.c_uint32),
        ("running", ctypes.c_uint32),
        ("configured_event_limit", ctypes.c_uint32),
        ("event_count", ctypes.c_uint32),

        ("initial_raw_inputs", ctypes.c_uint32),
        ("final_raw_inputs", ctypes.c_uint32),
        ("start_ticks", ctypes.c_uint32),
        ("stop_ticks", ctypes.c_uint32),

        ("stop_reason", ctypes.c_uint32),
        ("input_mask", ctypes.c_uint32),
        ("generation", ctypes.c_uint32),
        ("overflow_count", ctypes.c_uint32),

        ("ring", RawEdgeRecord * RAW_CAPACITY),
    ]


RAW_SHARED_SIZE = ctypes.sizeof(RawCaptureShared)
RAW_HEADER_SIZE = RawCaptureShared.ring.offset


@dataclass(frozen=True)
class RawReadConfig:
    devmem: str = "/dev/mem"
    physical_base: int = PRUSS_SHARED_PHYS_BASE


def raw_to_logical(raw_inputs: int) -> int:
    logical = 0
    for index, mask in enumerate(RAW_MASKS):
        if raw_inputs & mask:
            logical |= 1 << index
    return logical


def ticks_to_ns(ticks: int, tick_hz: int) -> float:
    return ticks * 1_000_000_000.0 / tick_hz


def ticks_to_us(ticks: int, tick_hz: int) -> float:
    return ticks * 1_000_000.0 / tick_hz


def _validate(shared: RawCaptureShared) -> None:
    if shared.magic != RAW_MAGIC:
        raise RuntimeError(
            f"raw capture magic 0x{shared.magic:08x}, expected 0x{RAW_MAGIC:08x}"
        )
    if shared.version != RAW_VERSION:
        raise RuntimeError(
            f"raw capture version {shared.version}, expected {RAW_VERSION}"
        )
    if shared.total_size != RAW_SHARED_SIZE:
        raise RuntimeError(
            f"raw capture size {shared.total_size}, host expects {RAW_SHARED_SIZE}"
        )
    if shared.capacity != RAW_CAPACITY:
        raise RuntimeError(
            f"raw capture capacity {shared.capacity}, host expects {RAW_CAPACITY}"
        )
    if shared.event_count > RAW_CAPACITY:
        raise RuntimeError(
            f"raw capture event_count {shared.event_count} exceeds capacity {RAW_CAPACITY}"
        )


def read_frozen_raw_capture(
    config: RawReadConfig = RawReadConfig(),
) -> RawCaptureShared:
    fd = os.open(config.devmem, os.O_RDONLY | os.O_SYNC)
    try:
        mapped = mmap.mmap(
            fd,
            PRUSS_SHARED_SIZE,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ,
            offset=config.physical_base,
        )
        try:
            header = RawCaptureShared.from_buffer_copy(mapped[:RAW_SHARED_SIZE])
            _validate(header)
            if header.running:
                raise RuntimeError(
                    "raw capture is still running; wait for event-limit auto-stop "
                    "or send RAW_STOP before reading the shared ring"
                )
            return header
        finally:
            mapped.close()
    finally:
        os.close(fd)


def raw_records(shared: RawCaptureShared) -> list[dict[str, int]]:
    _validate(shared)
    records: list[dict[str, int]] = []
    count = min(int(shared.event_count), RAW_CAPACITY)
    previous_logical = raw_to_logical(int(shared.initial_raw_inputs))

    for index in range(count):
        item = shared.ring[index]
        logical = raw_to_logical(int(item.raw_inputs))
        changed = logical ^ previous_logical
        records.append(
            {
                "index": index,
                "timestamp_ticks": int(item.timestamp_ticks),
                "raw_inputs": int(item.raw_inputs),
                "logical_inputs": logical,
                "changed_inputs": changed,
            }
        )
        previous_logical = logical

    return records


def _percentile(sorted_values: list[float], p: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * p
    lo = int(position)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = position - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }

    ordered = sorted(values)
    return {
        "count": len(values),
        "min": ordered[0],
        "mean": statistics.fmean(ordered),
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
        "max": ordered[-1],
    }


def summarize_ticks(
    values: list[int],
    tick_hz: int,
    *,
    scale: str,
) -> dict[str, object]:
    if scale == "us":
        converted = [ticks_to_us(value, tick_hz) for value in values]
        value_key = "value_us"
    else:
        converted = [ticks_to_ns(value, tick_hz) for value in values]
        value_key = "value_ns"

    result: dict[str, object] = dict(summarize(converted))
    counts = Counter(values)
    result["tick_histogram"] = [
        {
            "ticks": ticks,
            "count": counts[ticks],
            value_key: (
                ticks_to_us(ticks, tick_hz)
                if scale == "us"
                else ticks_to_ns(ticks, tick_hz)
            ),
        }
        for ticks in sorted(counts)
    ]
    return result


def _append_delta(
    destination: list[int],
    now: int,
    previous: int | None,
) -> None:
    if previous is None:
        return
    destination.append((now - previous) & 0xFFFFFFFF)


def analyze_raw_capture(
    shared: RawCaptureShared,
    *,
    min_deadtime_ns: float = 0.0,
) -> dict[str, object]:
    _validate(shared)
    tick_hz = int(shared.tick_hz)
    records = raw_records(shared)

    rise_last: list[int | None] = [None] * 6
    fall_last: list[int | None] = [None] * 6

    period_ticks: list[list[int]] = [[] for _ in range(6)]
    high_ticks: list[list[int]] = [[] for _ in range(6)]
    low_ticks: list[list[int]] = [[] for _ in range(6)]
    rise_count = [0] * 6
    fall_count = [0] * 6

    pending_hl: list[int | None] = [None] * 3
    pending_lh: list[int | None] = [None] * 3
    dead_hl_ticks: list[list[int]] = [[] for _ in range(3)]
    dead_lh_ticks: list[list[int]] = [[] for _ in range(3)]
    overlap_count = [0] * 3
    violation_count = [0] * 3
    overlap_active = [False] * 3

    previous_state = raw_to_logical(int(shared.initial_raw_inputs))

    for record in records:
        timestamp = int(record["timestamp_ticks"])
        state = int(record["logical_inputs"])
        changed = int(record["changed_inputs"])
        rise_bits = changed & state
        fall_bits = changed & previous_state

        for channel in range(6):
            bit = 1 << channel

            if rise_bits & bit:
                _append_delta(
                    period_ticks[channel],
                    timestamp,
                    rise_last[channel],
                )
                _append_delta(
                    low_ticks[channel],
                    timestamp,
                    fall_last[channel],
                )
                rise_last[channel] = timestamp
                rise_count[channel] += 1

            if fall_bits & bit:
                _append_delta(
                    high_ticks[channel],
                    timestamp,
                    rise_last[channel],
                )
                fall_last[channel] = timestamp
                fall_count[channel] += 1

        for pair in range(3):
            hi = pair * 2
            lo = hi + 1
            hi_bit = 1 << hi
            lo_bit = 1 << lo

            if fall_bits & hi_bit:
                pending_hl[pair] = timestamp

            if rise_bits & lo_bit:
                start = pending_hl[pair]
                if start is not None:
                    dt_ticks = (timestamp - start) & 0xFFFFFFFF
                    dt_ns = ticks_to_ns(dt_ticks, tick_hz)
                    dead_hl_ticks[pair].append(dt_ticks)
                    if min_deadtime_ns > 0 and dt_ns < min_deadtime_ns:
                        violation_count[pair] += 1
                pending_hl[pair] = None

            if fall_bits & lo_bit:
                pending_lh[pair] = timestamp

            if rise_bits & hi_bit:
                start = pending_lh[pair]
                if start is not None:
                    dt_ticks = (timestamp - start) & 0xFFFFFFFF
                    dt_ns = ticks_to_ns(dt_ticks, tick_hz)
                    dead_lh_ticks[pair].append(dt_ticks)
                    if min_deadtime_ns > 0 and dt_ns < min_deadtime_ns:
                        violation_count[pair] += 1
                pending_lh[pair] = None

            overlap_now = bool((state & hi_bit) and (state & lo_bit))
            if overlap_now and not overlap_active[pair]:
                overlap_count[pair] += 1
            overlap_active[pair] = overlap_now

        previous_state = state

    channels: dict[str, object] = {}
    for index, name in enumerate(CHANNEL_NAMES):
        channels[name] = {
            "rise_count": rise_count[index],
            "fall_count": fall_count[index],
            "period_us": summarize_ticks(period_ticks[index], tick_hz, scale="us"),
            "high_us": summarize_ticks(high_ticks[index], tick_hz, scale="us"),
            "low_us": summarize_ticks(low_ticks[index], tick_hz, scale="us"),
        }

    pairs: dict[str, object] = {}
    for index, name in enumerate(PAIR_NAMES):
        pairs[name] = {
            "deadtime_high_to_low_ns": summarize_ticks(
                dead_hl_ticks[index], tick_hz, scale="ns"
            ),
            "deadtime_low_to_high_ns": summarize_ticks(
                dead_lh_ticks[index], tick_hz, scale="ns"
            ),
            "overlap_count": overlap_count[index],
            "min_deadtime_violation_count": violation_count[index],
        }

    duration_ticks = (
        (int(shared.stop_ticks) - int(shared.start_ticks)) & 0xFFFFFFFF
        if shared.stop_ticks
        else 0
    )
    duration_us = ticks_to_us(duration_ticks, tick_hz) if tick_hz else None
    event_rate_hz = (
        int(shared.event_count) * 1_000_000.0 / duration_us
        if duration_us and duration_us > 0
        else None
    )

    return {
        "magic": f"0x{shared.magic:08x}",
        "version": int(shared.version),
        "generation": int(shared.generation),
        "tick_hz": tick_hz,
        "capacity": int(shared.capacity),
        "event_limit": int(shared.configured_event_limit),
        "event_count": int(shared.event_count),
        "overflow_count": int(shared.overflow_count),
        "stop_reason": int(shared.stop_reason),
        "start_ticks": int(shared.start_ticks),
        "stop_ticks": int(shared.stop_ticks),
        "capture_duration_us": duration_us,
        "event_rate_hz": event_rate_hz,
        "initial_raw_inputs": int(shared.initial_raw_inputs),
        "final_raw_inputs": int(shared.final_raw_inputs),
        "initial_logical_inputs": raw_to_logical(int(shared.initial_raw_inputs)),
        "final_logical_inputs": raw_to_logical(int(shared.final_raw_inputs)),
        "channels": channels,
        "pairs": pairs,
    }
