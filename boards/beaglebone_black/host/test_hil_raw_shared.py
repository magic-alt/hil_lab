import ctypes
import unittest

from hil_raw_shared import (
    RAW_CAPACITY,
    RAW_SHARED_SIZE,
    RawCaptureShared,
    analyze_raw_capture,
    raw_records,
    raw_to_logical,
)


UH_RAW = 1 << 1
UL_RAW = 1 << 2


class RawCaptureTests(unittest.TestCase):
    def make_capture(self) -> RawCaptureShared:
        shared = RawCaptureShared()
        shared.magic = 0x31574152
        shared.version = 1
        shared.total_size = ctypes.sizeof(RawCaptureShared)
        shared.tick_hz = 200_000_000
        shared.capacity = RAW_CAPACITY
        shared.running = 0
        shared.configured_event_limit = RAW_CAPACITY
        shared.initial_raw_inputs = UH_RAW
        shared.start_ticks = 0

        events = []
        for cycle in range(5):
            base = cycle * 10_000
            events.extend(
                [
                    (base + 4_860, 0),
                    (base + 5_000, UL_RAW),
                    (base + 9_860, 0),
                    (base + 10_000, UH_RAW),
                ]
            )

        shared.event_count = len(events)
        for index, (timestamp, raw) in enumerate(events):
            shared.ring[index].timestamp_ticks = timestamp
            shared.ring[index].raw_inputs = raw

        shared.stop_ticks = events[-1][0]
        shared.final_raw_inputs = events[-1][1]
        shared.stop_reason = 1
        return shared

    def test_abi_fits_shared_ram(self) -> None:
        self.assertEqual(RAW_SHARED_SIZE, 8256)
        self.assertLessEqual(RAW_SHARED_SIZE, 0x3000)

    def test_raw_mapping(self) -> None:
        self.assertEqual(raw_to_logical(UH_RAW), 0b000001)
        self.assertEqual(raw_to_logical(UL_RAW), 0b000010)
        self.assertEqual(raw_to_logical(UH_RAW | UL_RAW), 0b000011)

    def test_records_reconstruct_changed_bits(self) -> None:
        shared = self.make_capture()
        records = raw_records(shared)

        self.assertEqual(records[0]["logical_inputs"], 0)
        self.assertEqual(records[0]["changed_inputs"], 0b000001)
        self.assertEqual(records[1]["logical_inputs"], 0b000010)
        self.assertEqual(records[1]["changed_inputs"], 0b000010)

    def test_analyzer_reconstructs_20khz_700ns(self) -> None:
        result = analyze_raw_capture(
            self.make_capture(),
            min_deadtime_ns=600.0,
        )

        uh = result["channels"]["UH"]
        ul = result["channels"]["UL"]
        pair = result["pairs"]["U"]

        self.assertAlmostEqual(uh["period_us"]["mean"], 50.0)
        self.assertAlmostEqual(ul["period_us"]["mean"], 50.0)
        self.assertAlmostEqual(uh["high_us"]["mean"], 24.3)
        self.assertAlmostEqual(ul["high_us"]["mean"], 24.3)

        self.assertAlmostEqual(
            pair["deadtime_high_to_low_ns"]["mean"],
            700.0,
        )
        self.assertAlmostEqual(
            pair["deadtime_low_to_high_ns"]["mean"],
            700.0,
        )
        self.assertEqual(pair["overlap_count"], 0)
        self.assertEqual(pair["min_deadtime_violation_count"], 0)

        self.assertEqual(
            uh["period_us"]["tick_histogram"],
            [{"ticks": 10000, "count": 4, "value_us": 50.0}],
        )
        self.assertEqual(
            pair["deadtime_high_to_low_ns"]["tick_histogram"],
            [{"ticks": 140, "count": 5, "value_ns": 700.0}],
        )
        self.assertEqual(
            pair["deadtime_low_to_high_ns"]["tick_histogram"],
            [{"ticks": 140, "count": 5, "value_ns": 700.0}],
        )

    def test_analyzer_latches_short_deadtime_in_host(self) -> None:
        shared = self.make_capture()
        # Change one low-side rise from +140 ticks to +80 ticks.
        shared.ring[1].timestamp_ticks = 4_940

        result = analyze_raw_capture(shared, min_deadtime_ns=600.0)
        self.assertEqual(
            result["pairs"]["U"]["min_deadtime_violation_count"],
            1,
        )

        self.assertEqual(
            result["pairs"]["U"]["deadtime_high_to_low_ns"]["tick_histogram"],
            [
                {"ticks": 80, "count": 1, "value_ns": 400.0},
                {"ticks": 140, "count": 4, "value_ns": 700.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
