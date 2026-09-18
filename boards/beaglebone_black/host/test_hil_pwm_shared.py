import ctypes
import unittest

from hil_pwm_shared import (
    PWM_SHARED_SIZE,
    PwmShared,
    RING_CAPACITY,
    snapshot_to_dict,
)


class SharedAbiTests(unittest.TestCase):
    def test_shared_size_fits_pruss_shared_ram(self) -> None:
        self.assertEqual(PWM_SHARED_SIZE, 2416)
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


if __name__ == "__main__":
    unittest.main()
