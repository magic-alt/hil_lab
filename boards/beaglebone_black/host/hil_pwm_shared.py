from __future__ import annotations

import ctypes
import mmap
import os
import struct
import time
from dataclasses import asdict, dataclass

PRUSS_SHARED_PHYS_BASE = 0x4A310000
PRUSS_SHARED_SIZE = 0x3000
PWM_MAGIC = 0x314D5750
PWM_VERSION = 1
CHANNEL_NAMES = ("UH", "UL", "VH", "VL", "WH", "WL")
PAIR_NAMES = ("U", "V", "W")
RING_CAPACITY = 128


class ChannelSnapshot(ctypes.LittleEndianStructure):
    _fields_ = [
        ("period_ticks", ctypes.c_uint32),
        ("high_ticks", ctypes.c_uint32),
        ("low_ticks", ctypes.c_uint32),
        ("last_rise_ticks", ctypes.c_uint32),
        ("last_fall_ticks", ctypes.c_uint32),
        ("rise_count", ctypes.c_uint32),
        ("fall_count", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
    ]


class PairSnapshot(ctypes.LittleEndianStructure):
    _fields_ = [
        ("deadtime_high_to_low_ticks", ctypes.c_uint32),
        ("deadtime_low_to_high_ticks", ctypes.c_uint32),
        ("deadtime_high_to_low_count", ctypes.c_uint32),
        ("deadtime_low_to_high_count", ctypes.c_uint32),
        ("overlap_count", ctypes.c_uint32),
        ("violation_count", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
    ]


class EdgeRecord(ctypes.LittleEndianStructure):
    _fields_ = [
        ("timestamp_ticks", ctypes.c_uint32),
        ("logical_inputs", ctypes.c_uint32),
        ("changed_inputs", ctypes.c_uint32),
        ("fault_flags", ctypes.c_uint32),
    ]


class PwmShared(ctypes.LittleEndianStructure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("total_size", ctypes.c_uint32),
        ("seq_lock", ctypes.c_uint32),
        ("tick_hz", ctypes.c_uint32),
        ("channel_count", ctypes.c_uint32),
        ("pair_count", ctypes.c_uint32),
        ("ring_capacity", ctypes.c_uint32),
        ("running", ctypes.c_uint32),
        ("min_deadtime_ticks", ctypes.c_uint32),
        ("input_bits", ctypes.c_uint32),
        ("changed_bits", ctypes.c_uint32),
        ("last_timestamp_ticks", ctypes.c_uint32),
        ("event_seq", ctypes.c_uint32),
        ("ring_head", ctypes.c_uint32),
        ("ring_count", ctypes.c_uint32),
        ("fault_flags", ctypes.c_uint32),
        ("reserved0", ctypes.c_uint32),
        ("reserved1", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("channel", ChannelSnapshot * 6),
        ("pair", PairSnapshot * 3),
        ("ring", EdgeRecord * RING_CAPACITY),
    ]


PWM_SHARED_SIZE = ctypes.sizeof(PwmShared)
SEQ_LOCK_OFFSET = PwmShared.seq_lock.offset


@dataclass(frozen=True)
class SharedReadConfig:
    devmem: str = "/dev/mem"
    physical_base: int = PRUSS_SHARED_PHYS_BASE
    retries: int = 100


def _u32(buffer: bytes | mmap.mmap, offset: int) -> int:
    return struct.unpack_from("<I", buffer, offset)[0]


def read_consistent_snapshot(config: SharedReadConfig = SharedReadConfig()) -> PwmShared:
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
            for _ in range(config.retries):
                seq0 = _u32(mapped, SEQ_LOCK_OFFSET)
                if seq0 & 1:
                    continue

                blob = mapped[:PWM_SHARED_SIZE]
                seq_blob = _u32(blob, SEQ_LOCK_OFFSET)
                seq1 = _u32(mapped, SEQ_LOCK_OFFSET)

                if seq0 == seq_blob == seq1 and (seq1 & 1) == 0:
                    snapshot = PwmShared.from_buffer_copy(blob)
                    if snapshot.magic != PWM_MAGIC:
                        raise RuntimeError(
                            f"shared PWM magic 0x{snapshot.magic:08x}, expected 0x{PWM_MAGIC:08x}"
                        )
                    if snapshot.version != PWM_VERSION:
                        raise RuntimeError(
                            f"shared PWM version {snapshot.version}, expected {PWM_VERSION}"
                        )
                    if snapshot.total_size != PWM_SHARED_SIZE:
                        raise RuntimeError(
                            f"shared PWM size {snapshot.total_size}, host expects {PWM_SHARED_SIZE}"
                        )
                    return snapshot

            raise RuntimeError("could not obtain a stable shared-memory snapshot")
        finally:
            mapped.close()
    finally:
        os.close(fd)


def ticks_to_ns(ticks: int, tick_hz: int) -> float:
    return ticks * 1_000_000_000.0 / tick_hz


def snapshot_to_dict(snapshot: PwmShared, *, ring_limit: int = 16) -> dict[str, object]:
    tick_hz = int(snapshot.tick_hz)
    channels: dict[str, object] = {}
    for name, ch in zip(CHANNEL_NAMES, snapshot.channel):
        channels[name] = {
            "period_ticks": int(ch.period_ticks),
            "period_us": ch.period_ticks * 1_000_000.0 / tick_hz if tick_hz else None,
            "high_ticks": int(ch.high_ticks),
            "high_us": ch.high_ticks * 1_000_000.0 / tick_hz if tick_hz else None,
            "low_ticks": int(ch.low_ticks),
            "low_us": ch.low_ticks * 1_000_000.0 / tick_hz if tick_hz else None,
            "last_rise_ticks": int(ch.last_rise_ticks),
            "last_fall_ticks": int(ch.last_fall_ticks),
            "rise_count": int(ch.rise_count),
            "fall_count": int(ch.fall_count),
            "flags": int(ch.flags),
        }

    pairs: dict[str, object] = {}
    for name, pair in zip(PAIR_NAMES, snapshot.pair):
        pairs[name] = {
            "deadtime_high_to_low_ticks": int(pair.deadtime_high_to_low_ticks),
            "deadtime_high_to_low_ns": (
                ticks_to_ns(pair.deadtime_high_to_low_ticks, tick_hz) if tick_hz else None
            ),
            "deadtime_low_to_high_ticks": int(pair.deadtime_low_to_high_ticks),
            "deadtime_low_to_high_ns": (
                ticks_to_ns(pair.deadtime_low_to_high_ticks, tick_hz) if tick_hz else None
            ),
            "deadtime_high_to_low_count": int(pair.deadtime_high_to_low_count),
            "deadtime_low_to_high_count": int(pair.deadtime_low_to_high_count),
            "overlap_count": int(pair.overlap_count),
            "violation_count": int(pair.violation_count),
            "flags": int(pair.flags),
        }

    ring_count = min(int(snapshot.ring_count), RING_CAPACITY)
    emit_count = min(ring_count, max(0, ring_limit))
    records: list[dict[str, int]] = []
    if emit_count:
        start = (int(snapshot.ring_head) - emit_count) % RING_CAPACITY
        for offset in range(emit_count):
            record = snapshot.ring[(start + offset) % RING_CAPACITY]
            records.append(
                {
                    "timestamp_ticks": int(record.timestamp_ticks),
                    "logical_inputs": int(record.logical_inputs),
                    "changed_inputs": int(record.changed_inputs),
                    "fault_flags": int(record.fault_flags),
                }
            )

    return {
        "magic": f"0x{snapshot.magic:08x}",
        "version": int(snapshot.version),
        "total_size": int(snapshot.total_size),
        "seq_lock": int(snapshot.seq_lock),
        "tick_hz": tick_hz,
        "running": bool(snapshot.running),
        "min_deadtime_ticks": int(snapshot.min_deadtime_ticks),
        "min_deadtime_ns": (
            ticks_to_ns(snapshot.min_deadtime_ticks, tick_hz) if tick_hz else None
        ),
        "input_bits": int(snapshot.input_bits),
        "changed_bits": int(snapshot.changed_bits),
        "last_timestamp_ticks": int(snapshot.last_timestamp_ticks),
        "event_seq": int(snapshot.event_seq),
        "ring_head": int(snapshot.ring_head),
        "ring_count": ring_count,
        "fault_flags": int(snapshot.fault_flags),
        "channels": channels,
        "pairs": pairs,
        "recent_edges": records,
    }
