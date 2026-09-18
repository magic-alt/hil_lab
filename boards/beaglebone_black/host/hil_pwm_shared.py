from __future__ import annotations

import ctypes
import mmap
import os
import struct
from dataclasses import dataclass

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
PWM_SUMMARY_SIZE = PwmShared.ring.offset
SEQ_LOCK_OFFSET = PwmShared.seq_lock.offset
EVENT_SEQ_OFFSET = PwmShared.event_seq.offset
EDGE_RECORD_SIZE = ctypes.sizeof(EdgeRecord)


@dataclass(frozen=True)
class SharedReadConfig:
    devmem: str = "/dev/mem"
    physical_base: int = PRUSS_SHARED_PHYS_BASE
    retries: int = 1000


def _u32(buffer: bytes | bytearray | mmap.mmap, offset: int) -> int:
    return struct.unpack_from("<I", buffer, offset)[0]


def _validate_snapshot(snapshot: PwmShared) -> None:
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
    if snapshot.channel_count != len(CHANNEL_NAMES):
        raise RuntimeError(
            f"shared PWM channel_count {snapshot.channel_count}, "
            f"host expects {len(CHANNEL_NAMES)}"
        )
    if snapshot.pair_count != len(PAIR_NAMES):
        raise RuntimeError(
            f"shared PWM pair_count {snapshot.pair_count}, host expects {len(PAIR_NAMES)}"
        )
    if snapshot.ring_capacity != RING_CAPACITY:
        raise RuntimeError(
            f"shared PWM ring_capacity {snapshot.ring_capacity}, "
            f"host expects {RING_CAPACITY}"
        )


def _copy_ring_window(
    mapped: bytes | bytearray | mmap.mmap,
    full_blob: bytearray,
    *,
    start_slot: int,
    record_count: int,
) -> None:
    if record_count <= 0:
        return

    first_count = min(record_count, RING_CAPACITY - start_slot)
    first_src = RING_OFFSET = PWM_SUMMARY_SIZE + (start_slot * EDGE_RECORD_SIZE)
    first_len = first_count * EDGE_RECORD_SIZE
    full_blob[first_src : first_src + first_len] = mapped[
        first_src : first_src + first_len
    ]

    second_count = record_count - first_count
    if second_count:
        second_src = PWM_SUMMARY_SIZE
        second_len = second_count * EDGE_RECORD_SIZE
        full_blob[second_src : second_src + second_len] = mapped[
            second_src : second_src + second_len
        ]


def read_consistent_snapshot_from_buffer(
    mapped: bytes | bytearray | mmap.mmap,
    *,
    retries: int = 1000,
    ring_limit: int = 0,
) -> PwmShared:
    if retries <= 0:
        raise ValueError("retries must be > 0")
    if ring_limit < 0:
        raise ValueError("ring_limit must be >= 0")

    for _ in range(retries):
        seq0 = _u32(mapped, SEQ_LOCK_OFFSET)
        if seq0 & 1:
            continue

        # Only the fixed 368-byte statistics/control prefix participates in
        # the live seqlock copy. Copying the full 2416-byte struct at 80k+
        # edge events/s creates an unnecessarily small collision-free window.
        summary_blob = bytes(mapped[:PWM_SUMMARY_SIZE])
        seq_blob = _u32(summary_blob, SEQ_LOCK_OFFSET)
        seq1 = _u32(mapped, SEQ_LOCK_OFFSET)

        if seq0 != seq_blob or seq0 != seq1 or (seq1 & 1):
            continue

        full_blob = bytearray(PWM_SHARED_SIZE)
        full_blob[:PWM_SUMMARY_SIZE] = summary_blob
        summary = PwmShared.from_buffer_copy(full_blob)
        _validate_snapshot(summary)

        ring_count = min(int(summary.ring_count), RING_CAPACITY)
        emit_count = min(ring_count, ring_limit)
        if emit_count == 0:
            return summary

        if summary.running and emit_count >= RING_CAPACITY:
            raise RuntimeError(
                "a full 128-record ring cannot be snapshotted consistently "
                "while capture is running; stop capture first or use "
                "--ring-limit < 128"
            )

        start_slot = (int(summary.ring_head) - emit_count) % RING_CAPACITY

        # The writer publishes ring_head only after writing each complete
        # record. Therefore records before the frozen ring_head are complete.
        # They remain valid until enough new events wrap and overwrite them.
        _copy_ring_window(
            mapped,
            full_blob,
            start_slot=start_slot,
            record_count=emit_count,
        )

        event_seq_after = _u32(mapped, EVENT_SEQ_OFFSET)
        advanced = (event_seq_after - int(summary.event_seq)) & 0xFFFFFFFF

        # Earliest requested slot is overwritten only after more than
        # (capacity - emit_count) new records. If that happened, retry from a
        # fresh summary/ring_head instead of returning a torn history window.
        if advanced > (RING_CAPACITY - emit_count):
            continue

        snapshot = PwmShared.from_buffer_copy(full_blob)
        _validate_snapshot(snapshot)
        return snapshot

    if ring_limit:
        raise RuntimeError(
            "could not obtain a stable PWM summary/recent-edge window; "
            "use --ring-limit 0 for live statistics or stop capture before "
            "requesting a large ring snapshot"
        )

    raise RuntimeError(
        "could not obtain a stable PWM summary; input update rate is too high "
        "for the current host reader"
    )


def read_consistent_snapshot(
    config: SharedReadConfig = SharedReadConfig(),
    *,
    ring_limit: int = 0,
) -> PwmShared:
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
            return read_consistent_snapshot_from_buffer(
                mapped,
                retries=config.retries,
                ring_limit=ring_limit,
            )
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
        "summary_size": PWM_SUMMARY_SIZE,
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
