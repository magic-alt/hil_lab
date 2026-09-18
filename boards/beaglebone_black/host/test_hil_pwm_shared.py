import ctypes
import unittest

from hil_pwm_shared import (
    PWM_SHARED_SIZE,
    PWM_SUMMARY_SIZE,
    PwmShared,
    RING_CAPACITY,
    read_consistent_snapshot_from_buffer,
    snapshot_to_dict,
)


def make_shared_buffer() -> bytearray:
    shared = PwmShared()
    shared.magic = 0x314D5750
    shared.version = 1
    shared.total_size = ctypes.sizeof(PwmShared)
    shared.seq_lock = 2
    shared.tick_hz = 200_000_000
    shared.channel_count = 6
    shared.pair_count = 3
    shared.ring_capacity = RING_CAPACITY
    shared.running = 1
    shared.min_deadtime_ticks = 140
    return bytearray(bytes(shared))


class SharedAbiTests(unittest.TestCase):
    def test_shared_size_fits_pruss_shared_ram(self) -> None:
        self.assertEqual(PWM_SHARED_SIZE, 2416)
        self.assertEqual(PWM_SUMMARY_SIZE, 368)
        self.assertLess(PWM_SHARED_SIZE, 0x3000)

    def test_snapshot_conversion(self) -> None:
        shared = PwmShared()
        shared.magic = 0x314D5750
        shared.version = 1
        shared.total_size = ctypes.sizeof(PwmShared)
        shared.tick_hz = 200_000_000
        shared.running = 1
        shared.min_deadtime_ticks = 140
        shared.channel[0].period_ticks = 10_000
        shared.channel[0].high_ticks = 5_000
        shared.pair[0].deadtime_high_to_low_ticks = 140
        shared.ring_count = 1
        shared.ring_head = 1
        shared.ring[0].timestamp_ticks = 123
        shared.ring[0].logical_inputs = 1
        shared.ring[0].changed_inputs = 1

        result = snapshot_to_dict(shared, ring_limit=1)
        self.assertTrue(result["running"])
        self.assertEqual(result["min_deadtime_ns"], 700.0)
        self.assertEqual(result["channels"]["UH"]["period_us"], 50.0)
        self.assertEqual(result["pairs"]["U"]["deadtime_high_to_low_ns"], 700.0)
        self.assertEqual(result["recent_edges"][0]["timestamp_ticks"], 123)

    def test_split_reader_live_summary(self) -> None:
        blob = make_shared_buffer()
        raw = PwmShared.from_buffer(blob)
        raw.event_seq = 80_000
        raw.channel[0].period_ticks = 10_000
        raw.channel[0].high_ticks = 4_860
        raw.channel[0].low_ticks = 5_140
        raw.channel[0].rise_count = 20_000
        raw.channel[0].fall_count = 20_000
        raw.pair[0].deadtime_high_to_low_ticks = 140
        raw.pair[0].deadtime_low_to_high_ticks = 140

        snapshot = read_consistent_snapshot_from_buffer(blob, ring_limit=0)
        self.assertEqual(snapshot.event_seq, 80_000)
        self.assertEqual(snapshot.channel[0].period_ticks, 10_000)
        self.assertEqual(snapshot.pair[0].deadtime_high_to_low_ticks, 140)

    def test_split_reader_recent_ring_without_wrap(self) -> None:
        blob = make_shared_buffer()
        raw = PwmShared.from_buffer(blob)
        raw.event_seq = 100
        raw.ring_count = 8
        raw.ring_head = 8

        for index in range(8):
            raw.ring[index].timestamp_ticks = 1000 + index
            raw.ring[index].logical_inputs = index & 0x3
            raw.ring[index].changed_inputs = 1 << (index & 1)

        snapshot = read_consistent_snapshot_from_buffer(blob, ring_limit=4)
        result = snapshot_to_dict(snapshot, ring_limit=4)
        self.assertEqual(
            [item["timestamp_ticks"] for item in result["recent_edges"]],
            [1004, 1005, 1006, 1007],
        )

    def test_split_reader_recent_ring_wrap(self) -> None:
        blob = make_shared_buffer()
        raw = PwmShared.from_buffer(blob)
        raw.event_seq = 200
        raw.ring_count = RING_CAPACITY
        raw.ring_head = 3

        # Recent six records occupy slots 125,126,127,0,1,2.
        slots = [125, 126, 127, 0, 1, 2]
        for offset, slot in enumerate(slots):
            raw.ring[slot].timestamp_ticks = 5000 + offset
            raw.ring[slot].logical_inputs = offset & 0x3
            raw.ring[slot].changed_inputs = 1

        snapshot = read_consistent_snapshot_from_buffer(blob, ring_limit=6)
        result = snapshot_to_dict(snapshot, ring_limit=6)
        self.assertEqual(
            [item["timestamp_ticks"] for item in result["recent_edges"]],
            [5000, 5001, 5002, 5003, 5004, 5005],
        )

    def test_full_ring_requires_stopped_capture(self) -> None:
        blob = make_shared_buffer()
        raw = PwmShared.from_buffer(blob)
        raw.event_seq = RING_CAPACITY
        raw.ring_count = RING_CAPACITY
        raw.ring_head = 0
        raw.running = 1

        with self.assertRaisesRegex(RuntimeError, "stop capture first"):
            read_consistent_snapshot_from_buffer(blob, ring_limit=RING_CAPACITY)

        raw.running = 0
        snapshot = read_consistent_snapshot_from_buffer(
            blob,
            ring_limit=RING_CAPACITY,
        )
        self.assertFalse(snapshot.running)


if __name__ == "__main__":
    unittest.main()
