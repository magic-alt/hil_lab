import unittest

from hil_abz import (
    decode_config_flags,
    encode_config_flags,
    rpm_from_transition_ticks,
    transition_ticks_from_hz,
    transition_ticks_from_rpm,
)


class AbzHostMathTests(unittest.TestCase):
    def test_1000ppr_60rpm(self) -> None:
        ticks = transition_ticks_from_rpm(60.0, 1000, 200_000_000)
        self.assertEqual(ticks, 50_000)
        self.assertAlmostEqual(
            rpm_from_transition_ticks(ticks, 1000, 200_000_000),
            60.0,
        )

    def test_transition_rate(self) -> None:
        self.assertEqual(
            transition_ticks_from_hz(1_000_000.0, 200_000_000),
            200,
        )

    def test_flags(self) -> None:
        flags = encode_config_flags("reverse", 3)
        self.assertEqual(flags, 0x301)
        self.assertEqual(decode_config_flags(flags), ("reverse", 3))

    def test_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            transition_ticks_from_rpm(0, 1000, 200_000_000)
        with self.assertRaises(ValueError):
            encode_config_flags("forward", 4)


if __name__ == "__main__":
    unittest.main()
