import unittest

from hil_sensor import build_biss_frame, crc6_biss


class SensorProtocolTests(unittest.TestCase):
    def test_biss_crc_is_six_bits(self) -> None:
        for value in (0, 1, 0x12345, 0x3FFFF):
            crc = crc6_biss(value, 18, 1, 1)
            self.assertGreaterEqual(crc, 0)
            self.assertLess(crc, 64)

    def test_biss_frame_layout(self) -> None:
        frame, total_bits = build_biss_frame(0x155, 10, 1, 1)
        bits = format(frame, f"0{total_bits}b")
        self.assertEqual(total_bits, 21)
        self.assertEqual(bits[:3], "010")
        self.assertEqual(bits[3:13], format(0x155, "010b"))
        self.assertEqual(bits[13:15], "11")

    def test_biss_status_changes_crc(self) -> None:
        nominal = crc6_biss(0x1234, 16, 1, 1)
        error = crc6_biss(0x1234, 16, 0, 1)
        warning = crc6_biss(0x1234, 16, 1, 0)
        self.assertNotEqual(nominal, error)
        self.assertNotEqual(nominal, warning)


if __name__ == "__main__":
    unittest.main()
